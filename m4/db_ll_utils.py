#!/usr/bin/env python3
"""
db_ll_utils.py - Low-level database utilities for MemoriesDB

This module provides direct SQL call functionality and super-low level database
access. Everything else in the system should use this layer to interact with
the database for consistent error handling and connection management.
"""

import asyncio
import logging
import numpy as np
import numpy.typing as npt
import psycopg
import psycopg_pool
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector_async
import time
from typing import Any, Dict, List, Optional, Union, cast

from config import PG_USER, PG_PASS, PG_HOST, PG_PORT, PG_DB, DEBUG, DSN
from logging_setup import get_logger


logger = get_logger(__name__)

# Build Database Connection String
logger.info("Database connection configured with DSN: " +
            DSN.replace(PG_PASS, "***") if PG_PASS else DSN)

# Connection pool
_pool = None

# A simple module-level variable to store the current user ID
_CURRENT_USER_ID = '00000000-0000-0000-0000-000000000000'

def get_current_user_id() -> Optional[str]:
    """Get the current user ID from memory
    
    Returns:
        Optional[str]: The current user ID or None if not set
    """
    return _CURRENT_USER_ID

def set_current_user_id(user_id: str):
    """Set the current user ID in memory
    
    This sets the user ID in memory, and all subsequent database connections
    will automatically use this user ID for auditing purposes.
    
    Args:
        user_id: UUID string of the user to set as current
    """
    global _CURRENT_USER_ID
    _CURRENT_USER_ID = user_id
    logger.info(f"Set current user ID to {user_id}")
    pass

async def _init_connection(conn):
    """Initialize a database connection with the current user context
    
    This runs automatically when a connection is acquired from the pool.
    Sets both application_name for audit logging and app.current_user for RLS.
    Also registers the vector type for pgvector support.
    """
    # Register vector type for pgvector support
    await register_vector_async(conn)
    
    user_id = get_current_user_id()
    if user_id:
        print("USERID", user_id)
        await conn.execute(f"SET application_name = 'user:{user_id}'")
        await conn.execute("SELECT set_config('app.current_user', %s, false)", (str(user_id), ))
        await conn.commit()
        logger.debug(f"Initialized connection for user: {user_id}")
        pass
        
    return

def _register_cleanup_hook():
    import asyncio
    from functools import wraps

    loop = asyncio.get_event_loop()
    original_close = loop.close
    
    @wraps(original_close)
    def patched_close():
        # Clean up pool before loop closes
        if _pool:
            try:
                loop.run_until_complete(_pool.close())
            except RuntimeError:
                pass  # Loop might already be closing
            pass
        original_close()
        pass
    
    loop.close = patched_close
    pass

async def get_pool():
    """Get or create the database connection pool
    
    Each connection will be initialized with the current user context.
    """
    global _pool
    if _pool is None:
        _pool = psycopg_pool.AsyncConnectionPool(
            DSN, 
            min_size=1, 
            max_size=10,
            # We'll handle setting the user context when connections are acquired
            configure=_init_connection,
            open=False
        )
        _register_cleanup_hook()
        await _pool.open(wait=True)
        pass
    return _pool

async def query_fetchall(
    query: str,
    params: Optional[tuple] = None,
    as_dict: bool = False
):
    """Execute a SQL query and return all results at once
    
    Args:
        query: The SQL query to execute
        params: Optional parameters for the query
        as_dict: If True, return rows as dictionaries
    
    Returns:
        List of all query results
    """
    start_time = time.time()
    pool = await get_pool()
    
    async with pool.connection() as conn:
        if as_dict:
            conn.row_factory = dict_row
            
        async with conn.cursor() as cursor:
            await cursor.execute(query, params)
            results = await cursor.fetchall()
            
            duration = time.time() - start_time
            logger.debug(f"Query executed in {duration:.3f}s: {query[:100]}{'...' if len(query) > 100 else ''}")
            
            return results

async def query_fetchone(
    query: str,
    params: Optional[tuple] = None,
    as_dict: bool = False,
    raise_index_error = False
) -> Optional[Union[tuple, Dict[str, Any]]]:
    """Execute a SQL query and return a single row
    
    Args:
        query: The SQL query to execute
        params: Optional parameters for the query
        as_dict: If True, return row as dictionary
    
    Returns:
        A single row or None if no results
    """
    start_time = time.time()
    pool = await get_pool()
    
    # Simple direct implementation using context managers
    async with pool.connection() as conn:
        if as_dict:
            conn.row_factory = dict_row
            
        async with conn.cursor() as cursor:
            await cursor.execute(query, params)
            result = await cursor.fetchone()
            
            duration = time.time() - start_time
            logger.debug(f"Query executed in {duration:.3f}s: {query[:100]}{'...' if len(query) > 100 else ''}")

            # TODO: test this
            if raise_index_error and result is None:
                raise IndexError('row not found')

            return result

async def query(
    query: str,
    params: Optional[tuple] = None,
    as_dict: bool = False
):
    """Execute a SQL query and stream results one row at a time
    
    This function provides true streaming by yielding rows directly
    from the cursor without loading all results into memory.
    
    Args:
        query: The SQL query to execute
        params: Optional parameters for the query
        as_dict: If True, return rows as dictionaries
    
    Returns:
        An async generator that yields rows one at a time
    """
    start_time = time.time()
    pool = await get_pool()
    
    async with pool.connection() as conn:
        if as_dict:
            conn.row_factory = dict_row
            
        async with conn.cursor() as cursor:
            await cursor.execute(query, params)

            duration = time.time() - start_time
            logger.debug(f"Query executed in {duration:.3f}s: {query[:100]}{'...' if len(query) > 100 else ''}")

            # Reset timer to zero
            start_time = time.time()

            # Stream results directly - only one row in memory at a time
            while True:
                row = await cursor.fetchone()
                if row is None:
                    break
                yield row
            
            duration = time.time() - start_time
            logger.debug(f"Query streamed in {duration:.3f}s: {query[:100]}{'...' if len(query) > 100 else ''}")


async def execute(
    query: str,
    params: Optional[tuple] = None
) -> Optional[list]:
    """Execute a SQL statement and return results if there's a RETURNING clause.
    
    Args:
        query: The SQL statement to execute
        params: Optional parameters for the statement
        
    Returns:
        List of results if the query has a RETURNING clause, None otherwise
    """
    start_time = time.time()
    pool = await get_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(query, params)

            # TODO: A better way to do this would to just return the result no matter what, then try/catch the exception and return None
            
            # Check if the query has a RETURNING clause
            has_returning = 'RETURNING' in query.upper()
            
            if has_returning:
                result = await cursor.fetchall()
            else:
                result = None
                
            await conn.commit()
            
            duration = time.time() - start_time
            logger.debug(f"Statement executed in {duration:.3f}s: {query[:100]}{'...' if len(query) > 100 else ''}")
            
            return result


def ensure_float32(array: npt.ArrayLike) -> npt.NDArray[np.float32]:
    """Ensure input is a numpy float32 array.
    
    Args:
        array: Input array or array-like object
        
    Returns:
        np.ndarray with dtype=np.float32
        
    Raises:
        ValueError: If input cannot be converted to float32 array
    """
    if not isinstance(array, np.ndarray):
        array = np.asarray(array, dtype=np.float32)
    elif array.dtype != np.float32:
        array = array.astype(np.float32)
    return array


async def generate_db_tuid() -> str:
    """Generate a UUID using PostgreSQL's uuid-ossp extension
    
    This is more efficient than generating UUIDs in Python when you need to generate
    many UUIDs in a transaction, as it avoids network round trips.
    
    Returns:
        A new UUID string
    """
    raise Exception("Not implemented")
    result = await query_fetchone(
        "SELECT gen_random_uuid()::text as uuid"
    )
    return result['uuid']

def generate_tuid(node_id: bytes = None, clock_seq: int = None) -> str:
    """Generate a time-based UUID (version 1) that matches PostgreSQL's uuid-ossp
    
    This implements the same algorithm as PostgreSQL's uuid_generate_v1() function
    from the uuid-ossp extension. It generates a version 1 UUID using the current
    UTC time, a node ID (MAC address), and a clock sequence.
    
    Args:
        node_id: A 6-byte node identifier (default: uses host's MAC address)
        clock_seq: Clock sequence (default: randomly generated)
        
    Returns:
        A new UUID string in lowercase without curly braces
        (e.g., 'a0eebc99-9c0b-11ec-b909-0242ac120002')
    """
    import uuid
    import time
    
    # Get current UTC time in 100-nanosecond intervals since 1582-10-15 00:00:00
    nanoseconds = time.time_ns()
    uuid_epoch = 0x01b21dd213814000  # October 15, 1582 in 100ns intervals
    timestamp = (nanoseconds // 100) + uuid_epoch
    
    # Split into high, mid, and low parts
    time_low = timestamp & 0xffffffff
    time_mid = (timestamp >> 32) & 0xffff
    time_hi_version = ((timestamp >> 48) & 0x0fff) | 0x1000  # Sets version to 1
    
    # Generate clock sequence if not provided
    if clock_seq is None:
        import random
        clock_seq = random.getrandbits(14)  # 14-bit clock sequence
    
    clock_seq_low = clock_seq & 0xff
    clock_seq_hi_variant = ((clock_seq >> 8) & 0x3f) | 0x80  # Sets variant to RFC 4122
    
    # Get node ID (MAC address) if not provided
    if node_id is None:
        import uuid as uuid_module
        node_id = uuid_module.getnode().to_bytes(6, byteorder='big')
    
    # Pack into bytes
    uuid_bytes = (
        time_low.to_bytes(4, byteorder='big') +
        time_mid.to_bytes(2, byteorder='big') +
        time_hi_version.to_bytes(2, byteorder='big') +
        clock_seq_hi_variant.to_bytes(1, byteorder='big') +
        clock_seq_low.to_bytes(1, byteorder='big') +
        node_id
    )
    
    # Create UUID and return as string
    u = uuid.UUID(bytes=uuid_bytes)
    return str(u).lower()

async def pool_wrap(main, *args):
    try:
        pool = await get_pool()
        return await main(*args)
    finally:
        await pool.close()
        pass
    pass

# Additional utility functions can be added below as needed
