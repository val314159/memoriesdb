#!/usr/bin/env python3
"""
db_utils.py - Low-level database utilities for MemoriesDB

This module provides direct SQL call functionality and super-low level database
access. Everything else in the system should use this layer to interact with
the database for consistent error handling and connection management.
"""

import asyncio
import logging
import psycopg
import psycopg_pool
from psycopg.rows import dict_row
import time
from typing import Any, Dict, List, Optional, Union

from config import PG_USER, PG_PASS, PG_HOST, PG_PORT, PG_DB, DEBUG, DSN
from logging_setup import get_logger

logger = get_logger(__name__)

# Build Database Connection String
logger.info("Database connection configured with DSN: " +
            DSN.replace(PG_PASS, "***") if PG_PASS else DSN)

# Connection pool
_pool = None

# A simple module-level variable to store the current user ID
_CURRENT_USER_ID = None

def get_current_user_id() -> Optional[str]:
    """Get the current user ID from memory
    
    Returns:
        Optional[str]: The current user ID or None if not set
    """
    return _CURRENT_USER_ID

def set_current_user_id(user_id: str = None):
    """Set the current user ID in memory
    
    This sets the user ID in memory, and all subsequent database connections
    will automatically use this user ID for auditing purposes.
    
    Args:
        user_id: UUID string of the user to set as current
    """
    global _CURRENT_USER_ID
    _CURRENT_USER_ID = user_id
    logger.info(f"Set current user ID to {user_id}")

async def _init_connection(conn):
    """Initialize a database connection with the current user context
    
    This runs automatically when a connection is acquired from the pool.
    """
    # Set application_name to include the current user ID if available
    user_id = get_current_user_id()
    if user_id:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SET application_name = 'user:{user_id}'")
        logger.debug(f"Set connection application_name to user:{user_id}")
    return conn

async def get_pool():
    """Get or create the database connection pool
    
    Each connection will be initialized with the current user context.
    """
    global _pool
    if _pool is None:
        # Create connection pool with our connector function
        _pool = psycopg_pool.AsyncConnectionPool(
            DSN, 
            min_size=1, 
            max_size=10,
            # We'll handle setting the user context when connections are acquired
            configure=_init_connection
        )
        await _pool.wait()
    # The _init_connection function will handle setting the user context for each connection
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
):
    """Execute a SQL statement and return results if there are any
    
    Args:
        query: The SQL statement to execute
        params: Optional parameters for the statement
        
    Returns:
        List of rows if the query returns results (e.g., with RETURNING clause),
        None otherwise
    """
    start_time = time.time()
    pool = await get_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(query, params)
            
            # Check if this is a query that returns results (e.g., has RETURNING clause)
            if query.strip().upper().endswith('RETURNING ID;'):
                result = await cursor.fetchall()
                await conn.commit()
                return result
                
            await conn.commit()  # Commit for non-returning queries
            
            duration = time.time() - start_time
            logger.debug(f"Statement executed in {duration:.3f}s: {query[:100]}{'...' if len(query) > 100 else ''}")
            return None

async def query_fetchone(
    query: str,
    params: Optional[tuple] = None,
    as_dict: bool = False
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
            
            return result

async def get_memory_by_id(memory_id: str) -> Optional[Dict]:
    """Get a memory by its ID
    
    Args:
        memory_id: UUID of the memory to retrieve
    
    Returns:
        Dictionary with memory fields or None if not found
    """
    query = """
    SELECT id, content, content_hash, content_embedding, 
           created_by, updated_by
    FROM memories
    WHERE id = %s
    """
    return await query_fetchone(query, (memory_id,), as_dict=True)

async def create_memory(user_id: str, content: str) -> str:
    """Create a new memory
    
    Args:
        user_id: The UUID of the user creating the memory
        content: The content of the memory
        
    Returns:
        The UUID of the newly created memory
    """
    query = """
    INSERT INTO memories (user_id, content)
    VALUES (%s, %s)
    RETURNING id
    """
    result = await query_fetchone(query, (user_id, content))
    return result[0] if result else None

async def search_memories_vector(
    query_embedding: list,
    user_id: Optional[str] = None,
    limit: int = 10,
    similarity_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """Search memories by vector similarity using normalized vectors
    
    This function uses the <#> operator (negative inner product) which is optimized 
    for normalized vectors. The similarity is the negative of this value, which 
    provides a value from -1 (opposite vectors) to 1 (identical vectors).
    
    Args:
        query_embedding: Normalized vector embedding of the search query (must be unit length)
        user_id: Optional user ID to filter results
        limit: Maximum number of results to return
        similarity_threshold: Minimum similarity threshold (-1 to 1 scale, where 1 is identical).
                             Higher values return fewer but more relevant results.
        
    Returns:
        List of memories matching the query, sorted by decreasing similarity
    """
    user_filter = "AND user_id = %s" if user_id else ""
    params = []
    if user_id:
        params.append(user_id)
    
    # Using the WITH clause to avoid repeating the embedding calculation
    # <#> returns negative inner product, so we multiply by -1 to get similarity
    # Where similarity of 1 = identical vectors, 0 = orthogonal, -1 = opposite
    query = f"""
    WITH similarity_calc AS (
        SELECT id, user_id, content, created_at, updated_at,
               (content_embedding <#> %s) * -1 as similarity
        FROM memories
        WHERE content_embedding IS NOT NULL
        {user_filter}
    )
    SELECT * FROM similarity_calc
    WHERE similarity > %s
    ORDER BY similarity DESC
    LIMIT %s
    """
    
    # Add parameters in correct order
    params = [query_embedding] + params + [similarity_threshold, limit]
    
    results = []
    async for row in await query(query, tuple(params), as_dict=True):
        results.append(row)
    return results

async def create_memory_edge(source_id: str, target_id: str, relation: str) -> str:
    """Create a directed edge between two memories
    
    Args:
        source_id: Source memory UUID
        target_id: Target memory UUID
        relation: Type of relationship
        
    Returns:
        The UUID of the newly created edge
    """
    query = """
    INSERT INTO memory_edges (source_id, target_id, relation)
    VALUES (%s, %s, %s)
    RETURNING id
    """
    return await query_fetchone(query, (source_id, target_id, relation))

async def generate_uuid() -> str:
    """Generate a UUID using PostgreSQL's uuid-ossp extension
    
    This is more efficient than generating UUIDs in Python when you need to generate
    many UUIDs in a transaction, as it avoids network round trips.
    
    Returns:
        A new UUID string
    """
    result = await query_fetchone(
        "SELECT gen_random_uuid()::text as uuid"
    )
    return result['uuid']

def generate_uuid_ossp(node_id: bytes = None, clock_seq: int = None) -> str:
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


# Additional utility functions can be added below as needed
