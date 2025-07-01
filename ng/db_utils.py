#!/usr/bin/env python3
"""
db_utils.py - Low-level database utilities for MemoriesDB

This module provides direct SQL call functionality and super-low level database
access. Everything else in the system should use this layer to interact with
the database for consistent error handling and connection management.
"""

import asyncio
import psycopg
from psycopg.rows import dict_row
import time
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    # In newer versions of psycopg, the pool is in a separate package
    from psycopg_pool import AsyncConnectionPool
    has_pool_package = True
except ImportError:
    # Fall back to psycopg's built-in pool if available
    has_pool_package = False

from config import DSN
from logging_setup import get_logger

# Get configured logger
logger = get_logger(__name__)

# Connection pool
_pool = None

async def get_pool():
    """Get or create the database connection pool"""
    global _pool
    if _pool is None:
        # Create connection pool
        if has_pool_package:
            # Use dedicated pool package
            _pool = AsyncConnectionPool(DSN, min_size=1, max_size=10)
            await _pool.open()
        else:
            # Fallback to creating individual connections as needed
            logger.warning("AsyncConnectionPool not available, will create individual connections")
        logger.info(f"Database connection configured with DSN: {DSN.replace(DSN.split('@')[0], '***')}")
    return _pool

async def execute_query(
    query: str,
    params: Optional[tuple] = None,
    as_dict: bool = False
):
    """Execute a SQL query and return an async iterator for streaming results
    
    Args:
        query: The SQL query to execute
        params: Optional parameters for the query
        as_dict: If True, return rows as dictionaries
    
    Returns:
        AsyncIterator yielding rows one at a time
    """
    pool = await get_pool()
    start_time = time.time()
    conn = None
    cursor = None
    
    try:
        # Handle both pooled and direct connections
        if has_pool_package and pool is not None:
            # Use connection from pool
            conn = await pool.connection()
        else:
            # Create individual connection
            conn = await psycopg.AsyncConnection.connect(DSN)
        
        if as_dict:
            conn.row_factory = dict_row
            
        # Use server-side named cursor for streaming
        cursor = await conn.cursor(name=f"stream_{int(time.time()*1000)}")
        await cursor.execute(query, params)
        
        # Return an async generator
        async def result_generator():
            try:
                async for row in cursor:
                    yield row
            finally:
                # Clean up cursor and connection when done
                await cursor.close()
                if conn and not has_pool_package:
                    await conn.close()
                    
        duration = time.time() - start_time
        logger.debug(f"Query executed in {duration:.3f}s: {query[:100]}{'...' if len(query) > 100 else ''}")
        return result_generator()
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Query failed after {duration:.3f}s: {query[:100]}{'...' if len(query) > 100 else ''}")
        logger.error(f"Error: {str(e)}")
        # Clean up resources on error
        if cursor and not cursor.closed:
            await cursor.close()
        if conn and not has_pool_package:
            await conn.close()
        raise

async def execute_query_fetchone(
    query: str,
    params: Optional[tuple] = None,
    as_dict: bool = False
) -> Optional[Union[tuple, Dict[str, Any]]]:
    """Execute a SQL query and return a single row
    
    A thin wrapper around execute_query that returns just the first row or None
    
    Args:
        query: The SQL query to execute
        params: Optional parameters for the query
        as_dict: If True, return row as dictionary
    
    Returns:
        A single row or None if no results
    """
    result_gen = await execute_query(query, params, as_dict)
    try:
        # Just get the first result
        return await anext(result_gen)
    except StopAsyncIteration:
        # No results found
        return None

async def get_memory_by_id(memory_id: str) -> Optional[Dict[str, Any]]:
    """Get a memory by ID
    
    Args:
        memory_id: The UUID of the memory to retrieve
        
    Returns:
        Memory data as a dictionary or None if not found
    """
    query = """
    SELECT id, user_id, content, content_hash, content_embedding, created_at, updated_at
    FROM memories
    WHERE id = %s
    """
    return await execute_query_fetchone(query, (memory_id,), as_dict=True)

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
    result = await execute_query_fetchone(query, (user_id, content))
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
    async for row in await execute_query(query, tuple(params), as_dict=True):
        results.append(row)
    return results

async def create_memory_edge(from_id: str, to_id: str, edge_type: str) -> str:
    """Create a directed edge between two memories
    
    Args:
        from_id: Source memory UUID
        to_id: Target memory UUID
        edge_type: Type of relationship
        
    Returns:
        The UUID of the newly created edge
    """
    query = """
    INSERT INTO memory_edges (from_id, to_id, edge_type)
    VALUES (%s, %s, %s)
    RETURNING id
    """
    result = await execute_query_fetchone(query, (from_id, to_id, edge_type))
    return result[0] if result else None

# Additional utility functions can be added below as needed
