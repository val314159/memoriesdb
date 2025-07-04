#!/usr/bin/env python3
"""
db_utils.py - Low-level database utilities for MemoriesDB

this only touches the database with calls in db_ll_utils.py
most other modules will use this or higher level .py files
"""

from db_ll_utils import *

from logging_setup import get_logger

logger = get_logger(__name__)


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

async def create_memory(
    content: str, 
    user_id: Optional[str] = None,
    kind: Optional[str] = None,
    metadata: Optional[dict] = None,
    content_embedding: Optional[npt.ArrayLike] = None
) -> str:
    """Create a new memory
    
    Args:
        content: The content of the memory (required)
        user_id: Optional UUID of the user creating the memory. 
                If not provided, uses the current user context.
        kind: Optional type/category of the memory
        metadata: Optional JSON metadata to store with the memory
        content_embedding: Optional vector embedding of the content
        
    Returns:
        The UUID of the newly created memory
        
    Raises:
        ValueError: If content is empty or no user context is available
    """
    if not content:
        raise ValueError("Content cannot be empty")
        
    # Get user from context if not provided
    if not user_id:
        user_id = get_current_user_id()
        if not user_id:
            raise ValueError("No user context available. Call set_current_user_id() first or provide user_id.")
    
    query = """
    INSERT INTO memories (
        content, 
        kind, 
        _metadata, 
        content_embedding,
        created_by, 
        updated_by
    )
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    
    # Prepare parameters
    params = (
        content,
        kind,
        psycopg.types.json.Jsonb(metadata) if metadata else None,
        Vector(_ensure_float32(content_embedding).tolist()) if content_embedding is not None else None,
        user_id,
        user_id
    )
    
    try:
        result = await query_fetchone(query, params)
        if not result:
            raise ValueError("Failed to create memory: no ID returned")
        return result[0]
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise

async def search_memories_vector(
    query_embedding: npt.ArrayLike,
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
        user_id: Optional user ID to filter results by created_by
        limit: Maximum number of results to return
        similarity_threshold: Minimum similarity threshold (-1 to 1 scale, where 1 is identical).
                             Higher values return fewer but more relevant results.
        
    Returns:
        List of memories matching the query, sorted by decreasing similarity
    """
    # Ensure input is float32 numpy array
    query_embedding = _ensure_float32(query_embedding)
    
    # Convert to list for psycopg
    query_embedding_list = query_embedding.tolist()
    
    # Using the WITH clause to avoid repeating the embedding calculation
    # <#> returns negative inner product, so we multiply by -1 to get similarity
    # Where similarity of 1 = identical vectors, 0 = orthogonal, -1 = opposite
    query = """
    WITH similarity_calc AS (
        SELECT id, content, content_hash, created_by, updated_by,
               (content_embedding <#> %s) * -1 as similarity
        FROM memories
        WHERE content_embedding IS NOT NULL
        AND _deleted_at IS NULL
    """
    
    params = [query_embedding_list]
    
    # Add user filter if provided
    if user_id:
        query += " AND created_by = %s"
        params.append(user_id)
    
    # Complete the query
    query += """
    )
    SELECT * FROM similarity_calc
    WHERE similarity > %s
    ORDER BY similarity DESC
    LIMIT %s
    """
    
    # Add remaining parameters
    params.extend([similarity_threshold, limit])
    
    # Execute the query and get results
    results = await query_fetchall(query, tuple(params), as_dict=True)
    
    # Ensure similarity scores are float32
    for result in results:
        if 'similarity' in result:
            result['similarity'] = float(result['similarity'])  # Keep as Python float for JSON serialization
    
    return results

async def create_memory_edge(
    source_id: str, 
    target_id: str, 
    relation: str,
    strength: Optional[float] = None,
    confidence: Optional[float] = None,
    metadata: Optional[dict] = None
) -> str:
    """Create a directed edge between two memories
    
    Args:
        source_id: Source memory UUID
        target_id: Target memory UUID
        relation: Type of relationship (lowercase with underscores)
        strength: Optional strength of the relationship (-1.1 to 1.1)
        confidence: Optional confidence level (0.0 to 1.0)
        metadata: Optional JSON metadata
        
    Returns:
        The UUID of the newly created edge
        
    Raises:
        ValueError: If source_id equals target_id (self-reference)
    """
    if source_id == target_id:
        raise ValueError("Cannot create self-referential edge")
    
    # Get current user ID for created_by/updated_by
    user_id = get_current_user_id()
    if not user_id:
        raise ValueError("No current user set. Call set_current_user_id() first.")
    
    # Prepare query and parameters
    query = """
    INSERT INTO memory_edges 
        (source_id, target_id, relation, strength, confidence, _metadata, created_by, updated_by)
    VALUES 
        (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    
    result = await query_fetchone(
        query, 
        (
            source_id, 
            target_id, 
            relation,
            strength,
            confidence,
            psycopg.types.json.Jsonb(metadata) if metadata else None,
            user_id,
            user_id
        )
    )
    
    return result[0] if result else None



# Additional utility functions can be added below as needed
