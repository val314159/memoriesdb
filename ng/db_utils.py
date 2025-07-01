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
logged_dsn = DSN.replace(PG_PASS, "***") if PG_PASS else DSN
logger.info(f"Database connection configured with DSN: {logged_dsn}")

# Connection pool
_pool = None

async def get_pool():
    """Get or create the database connection pool"""
    global _pool
    
    if not _pool:
        _pool = psycopg_pool.AsyncConnectionPool(DSN, min_size=1, max_size=10)
        await _pool.wait()
            
    return _pool

async def execute_query(
    query: str,
    params: Optional[tuple] = None,
    as_dict: bool = False
):
    """Execute a SQL query and return all results
    
    Args:
        query: The SQL query to execute
        params: Optional parameters for the query
        as_dict: If True, return rows as dictionaries
    
    Returns:
        List of query results
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

async def execute_query_fetchone(
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
