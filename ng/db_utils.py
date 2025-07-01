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
from psycopg.rows import dict_row
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from config import DSN, DEBUG

# Set up logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Connection pool
_pool = None

async def get_pool() -> psycopg.AsyncConnectionPool:
    """Get or create the database connection pool"""
    global _pool
    if _pool is None:
        # Create connection pool
        _pool = await psycopg.AsyncConnectionPool.from_pool_params(
            conninfo=DSN,
            min_size=1,
            max_size=10,
            open=False  # Don't open connections yet
        )
        logger.info(f"Connection pool created with DSN: {DSN.replace(DSN.split('@')[0], '***')}")
    return _pool

async def execute_query(
    query: str,
    params: Optional[tuple] = None,
    fetch: bool = False,
    fetch_one: bool = False,
    as_dict: bool = False
) -> Union[List[tuple], Dict[str, Any], None]:
    """Execute a SQL query and optionally return results
    
    Args:
        query: The SQL query to execute
        params: Optional parameters for the query
        fetch: If True, fetch and return all results
        fetch_one: If True, fetch and return only the first row
        as_dict: If True, return results as dictionaries
    
    Returns:
        Query results or None
    """
    pool = await get_pool()
    start_time = time.time()
    
    try:
        async with pool.connection() as conn:
            if as_dict:
                conn.row_factory = dict_row
                
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                
                if fetch_one:
                    result = await cur.fetchone()
                elif fetch:
                    result = await cur.fetchall()
                else:
                    result = None
                    
                duration = time.time() - start_time
                logger.debug(f"Query executed in {duration:.3f}s: {query[:100]}{'...' if len(query) > 100 else ''}")
                return result
                
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Query failed after {duration:.3f}s: {query[:100]}{'...' if len(query) > 100 else ''}")
        logger.error(f"Error: {str(e)}")
        raise

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
    return await execute_query(query, (memory_id,), fetch_one=True, as_dict=True)

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
    result = await execute_query(query, (user_id, content), fetch_one=True)
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
    
    return await execute_query(query, tuple(params), fetch=True, as_dict=True)

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
    result = await execute_query(query, (from_id, to_id, edge_type), fetch_one=True)
    return result[0] if result else None

# Additional utility functions can be added below as needed
