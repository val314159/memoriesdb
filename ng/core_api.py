#!/usr/bin/env python3
"""
core_api.py - Medium-level API for MemoriesDB

This module wraps the low-level database functions from db_utils.py 
into more logical operations that handle common workflows.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

import db_utils
from config import DEBUG, OLLAMA_URL, EMBEDDING_MODEL, CHAT_MODEL

# Set up logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Optional import for embeddings generation
try:
    import ollama
    has_ollama = True
except ImportError:
    logger.warning("Ollama not available. Using debug mode for embeddings")
    has_ollama = False

# ----------------------
# Memory Operations
# ----------------------

async def create_memory_with_embedding(user_id: str, content: str) -> str:
    """Create a new memory and trigger the embedding generation process
    
    This is the primary function to use when adding new memories.
    The SQL triggers will automatically schedule it for embedding.
    
    Args:
        user_id: The UUID of the user creating the memory
        content: The content of the memory
        
    Returns:
        The UUID of the newly created memory
    """
    # Create the memory record which will trigger embedding_schedule
    memory_id = await db_utils.create_memory(user_id, content)
    
    if not memory_id:
        logger.error(f"Failed to create memory for user {user_id}")
        return None
    
    logger.info(f"Memory created with ID {memory_id}, embedding scheduled")
    return memory_id

async def get_memory(memory_id: str) -> Dict[str, Any]:
    """Get a memory by its ID with additional context
    
    Args:
        memory_id: The UUID of the memory to retrieve
        
    Returns:
        Memory data with additional context
    """
    memory = await db_utils.get_memory_by_id(memory_id)
    
    if not memory:
        logger.warning(f"Memory not found: {memory_id}")
        return None
    
    # Get connected memories (edges)
    connected = await get_connected_memories(memory_id)
    memory['connected'] = connected
    
    return memory

async def get_connected_memories(memory_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Get memories connected to the given memory ID
    
    Args:
        memory_id: The UUID of the memory to find connections for
        
    Returns:
        Dictionary with incoming and outgoing connections
    """
    query_out = """
    SELECT e.id as edge_id, e.edge_type, e.to_id as connected_id, 
           m.content as connected_content
    FROM memory_edges e
    JOIN memories m ON e.to_id = m.id
    WHERE e.from_id = %s
    """
    
    query_in = """
    SELECT e.id as edge_id, e.edge_type, e.from_id as connected_id,
           m.content as connected_content
    FROM memory_edges e
    JOIN memories m ON e.from_id = m.id
    WHERE e.to_id = %s
    """
    
    outgoing = await db_utils.execute_query(query_out, (memory_id,), fetch=True, as_dict=True) or []
    incoming = await db_utils.execute_query(query_in, (memory_id,), fetch=True, as_dict=True) or []
    
    return {
        "outgoing": outgoing,
        "incoming": incoming
    }

# ----------------------
# Search Operations
# ----------------------

async def generate_embedding(text: str) -> List[float]:
    """Generate an embedding vector for the given text
    
    Args:
        text: The text to generate an embedding for
        
    Returns:
        List of floats representing the embedding vector
    """
    if DEBUG and not has_ollama:
        # Generate a random vector in debug mode
        import random
        return [random.uniform(-1, 1) for _ in range(1536)]
    
    try:
        # Use Ollama for embeddings
        response = await ollama.embeddings(model=EMBEDDING_MODEL, prompt=text)
        return response['embedding']
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise

async def semantic_search(query: str, user_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Search memories using semantic similarity
    
    Args:
        query: The search query text
        user_id: Optional user ID to filter results
        limit: Maximum number of results
        
    Returns:
        List of matching memories with similarity scores
    """
    # Generate embedding for the query
    query_embedding = await generate_embedding(query)
    
    # Perform vector search
    results = await db_utils.search_memories_vector(
        query_embedding=query_embedding,
        user_id=user_id,
        limit=limit
    )
    
    return results

# ----------------------
# Graph Operations
# ----------------------

async def connect_memories(from_id: str, to_id: str, edge_type: str = "related") -> str:
    """Connect two memories with a directed edge
    
    Args:
        from_id: Source memory UUID
        to_id: Target memory UUID
        edge_type: Type of relationship
        
    Returns:
        The UUID of the newly created edge
    """
    # Ensure both memories exist
    from_memory = await db_utils.get_memory_by_id(from_id)
    to_memory = await db_utils.get_memory_by_id(to_id)
    
    if not from_memory or not to_memory:
        missing = [] if from_memory else [from_id]
        if not to_memory:
            missing.append(to_id)
        logger.error(f"Cannot connect memories: IDs not found: {missing}")
        return None
    
    # Create the edge
    edge_id = await db_utils.create_memory_edge(from_id, to_id, edge_type)
    
    if edge_id:
        logger.info(f"Created edge {edge_id} from {from_id} to {to_id} of type '{edge_type}'")
    
    return edge_id
