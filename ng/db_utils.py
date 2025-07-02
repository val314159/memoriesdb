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
) -> None:
    """Execute a SQL statement that doesn't return results (INSERT, UPDATE, DELETE, DDL, etc.)
    
    Args:
        query: The SQL statement to execute
        params: Optional parameters for the statement
    """
    start_time = time.time()
    pool = await get_pool()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(query, params)
            await conn.commit()  # Explicitly commit changes
            
            duration = time.time() - start_time
            logger.debug(f"Statement executed in {duration:.3f}s: {query[:100]}{'...' if len(query) > 100 else ''}")

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

# Additional utility functions can be added below as needed
