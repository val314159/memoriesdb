from db_ll_sync import *

#import uuid
#from typing import Any, Dict, List, Optional, Tuple, Union

from config import OLLAMA_URL, EMBEDDING_MODEL, CHAT_MODEL
from logging_setup import get_logger
logger = get_logger(__name__)

# Optional import for embeddings generation
try:
    import ollama
    has_ollama = True
except ImportError:
    logger.warning("Ollama not available. Using debug mode for embeddings")
    has_ollama = False

def get_memories_by_uuid(created_by: str, suffix='') -> List:
    query = """
    SELECT id, kind, content, content_hash, content_embedding, _metadata,
           created_by, updated_by
    FROM memories
    WHERE created_by = %s and _deleted_at IS NULL
    """
    if suffix: query += ' ' + suffix
    try:
        conn = psycopg.connect(DSN, row_factory=dict_row)
    except:
        conn = psycopg.connect(DSN2,row_factory=dict_row)
        pass
    cursor = conn.cursor()
    cursor.execute(query, (created_by,))
    for row in cursor:
        yield row
        pass
    return

def get_memory_by_id(memory_id: str) -> Optional[Dict]:
    """Get a memory by its ID
    
    Args:
        memory_id: UUID of the memory to retrieve
    
    Returns:
        Dictionary with memory fields or None if not found
    """
    query = """
    SELECT id, kind, content, content_hash, content_embedding, _metadata,
           created_by, updated_by
    FROM memories
    WHERE id = %s
    """
    conn = psycopg.connect(DSN, row_factory=dict_row)
    cursor = conn.cursor()
    cursor.execute(query, (memory_id,))
    ret = cursor.fetchone()
    metadata = ret.pop('_metadata')
    ret.update(metadata)
    return ret

def get_edges_by_source(edge_id: str) -> Optional[Dict]:
    conn = psycopg.connect(DSN, row_factory=dict_row)
    cursor = conn.cursor()
    query = """
    SELECT id, source_id, target_id, relation,
    strength, confidence, _metadata, created_by, updated_by
    FROM memory_edges
    WHERE source_id = %s
    """
    cursor.execute(query, (edge_id,))
    for row in cursor:
        yield row
        pass
    pass

def get_memories_by_target(memory_id: str, suffix: str=''):
    conn = psycopg.connect(DSN, row_factory=dict_row)
    cursor = conn.cursor()
    query = """
    SELECT id, kind, content, content_hash, content_embedding,
           _metadata, created_by, updated_by
    FROM memories
    WHERE id IN (
      SELECT source_id FROM memory_edges WHERE target_id = %s
    )
    """ + suffix
    cursor.execute(query, (memory_id,))
    for row in cursor:
        row.update(row.pop('_metadata'))
        yield row
        pass
    pass

def get_edges_by_target(edge_id: str) -> Optional[Dict]:
    conn = psycopg.connect(DSN, row_factory=dict_row)
    cursor = conn.cursor()
    query = """
    SELECT id, source_id, target_id, relation,
    strength, confidence, _metadata, created_by, updated_by
    FROM memory_edges
    WHERE target_id = %s
    """
    cursor.execute(query, (edge_id,))
    for row in cursor:
        yield row
        pass
    pass

def get_edge_by_id(edge_id: str) -> Optional[Dict]:
    """Get an edge by its ID
    
    Args:
        edge_id: UUID of the memory edge to retrieve
    
    Returns:
        Dictionary with memory edge fields or None if not found
    """
    query = """
    SELECT id, source_id, target_id, relation,
    strength, confidence, _metadata, created_by, updated_by
    FROM memory_edges
    WHERE id = %s
    """
    conn = psycopg.connect(DSN, row_factory=dict_row)
    cursor = conn.cursor()
    cursor.execute(query, (edge_id,), as_dict=True)
    ret = cursor.fetchone()
    if ret:  ret.update(ret.pop('_metadata'))
    return ret

def create_memory(
    content: str, 
    user_id: Optional[str] = None,
    kind: Optional[str] = None,
    metadata: Optional[dict] = None,
    content_embedding: Optional[npt.ArrayLike] = None,
    **kw
) -> str: # uuid
    conn = psycopg.connect(DSN)
    cursor = conn.cursor()
    if not content:
        content = ''
        pass
    if type(metadata) == dict:
        metadata.update(kw)
    else:
        metadata = kw
        pass
    query = """
    INSERT INTO memories (
        content, 
        kind, 
        _metadata, 
        content_embedding,
        created_by, 
        updated_by)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id
    """

    if not user_id:
        user_id = get_current_user_id()
    if not user_id:
        raise ValueError("No current user set. Call set_current_user_id() first.")

    params = (
        content,
        kind,
        psycopg.types.json.Jsonb(metadata) if metadata else '{}',
        Vector(_ensure_float32(content_embedding).tolist()) if content_embedding is not None else None,
        user_id,
        user_id
    )
    cursor.execute(query, params)
    record_uuid = cursor.fetchone()[0]
    conn.commit()
    return record_uuid

def create_memory_edge(
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
    conn = psycopg.connect(DSN)
    cursor = conn.cursor()
    query = """
    INSERT INTO memory_edges (
        source_id,
        target_id,
        relation,
        strength,
        confidence,
        _metadata,
        created_by,
        updated_by)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    params = (
        source_id, 
        target_id, 
        relation,
        strength,
        confidence,
        psycopg.types.json.Jsonb(metadata) if metadata else '{}',
        user_id,
        user_id
    )
    try:
        cursor.execute(query, params)
        result = cursor.fetchone()
        if not result:
            raise ValueError("Failed to create memory: no ID returned")
        conn.commit()
        return result[0]
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise

def check_valid_uuid(uuid):
    conn = psycopg.connect(DSN)
    cursor = conn.cursor()
    password = os.getenv('USER_PASSWORD', 'el passwordo')
    try:        
        cursor.execute("SELECT md5(%s)=digest FROM users"
                       " WHERE users.id=%s LIMIT 1",
                       (password, uuid))
        if row:= cursor.fetchone():
            if row[-1]:
                print("PASSWORD MATCH, USER IS GOOD!")
                return uuid
            else:
                print("PASSWORD MISMATCH")
                raise SystemExit(6)
        else:
            print("user not found!", uuid)
            raise SystemExit(5)
    except psycopg.errors.InvalidTextRepresentation:
        print("WTF DUDE ARE YOU HIGH DID YOU THINK THIS WAS A VALID UUID??", uuid)
        raise SystemExit(4)


def load_simplified_convo(convo_id, reverse=False):
    return simplify_convo(load_convo(convo_id, reverse))


def simplify_convo(convo):
    """
    turns a complex array of dicts
    into the minumum we need to send to the context window
    """
    for msg in convo:
        kind = msg.get('kind')
        if kind in ('history', 'partial'):
            data = dict(role=msg['role'],
                        content=msg['content'])
            done = msg.get('done', None)
            if done is not None:
                data['done'] = done
            if role:= msg.get('role'):
                data['role'] = role
            if images:= msg.get('images'):
                data['images'] = images
            if tool_name:= msg.get('tool_name'):
                data['tool_name'] = tool_name
            if tool_calls:= msg.get('tool_calls'):
                data['tool_calls'] = tool_calls
            if thinking:= msg.get('thinking'):
                data['thinking'] = thinking
            yield data
        elif kind == 'session':
            pass
        else:
            NO_WAY


def load_convo(suid, reverse=False):
    session = get_memory_by_id(suid)
    suffix = ' ORDER BY ID DESC ' if reverse else ''
    return get_memories_by_target( session['id'], suffix )
        

def store_convo(history, title):
    uuid = get_current_user_id()
    suid = create_memory(title, uuid, kind='session')
    for h in history:
        h['user_id'] = uuid
        h['active'] = True
        muid = create_memory(**h)
        euid = create_memory_edge(muid, suid, 'belongs_to')
        pass
    return suid

def get_user_sessions(uuid):
    return get_memories_by_uuid(uuid, " AND kind='session'")

def get_last_session(uuid):
    suffix = " AND kind='session' ORDER BY id DESC LIMIT 1"
    for row in get_memories_by_uuid(uuid, suffix):
        print(f"Loading Session {row['id']}: {row['content']}")
        return row

def generate_embedding(text: str) -> List[float]:
    """Generate a normalized embedding vector for the given text
    
    Args:
        text: The text to generate an embedding for
        
    Returns:
        List of floats representing the normalized embedding vector (unit length)
    """
    if DEBUG and not has_ollama:
        # Generate a random vector in debug mode
        import random
        import math
        
        # Generate random vector
        raw_vector = [random.uniform(-1, 1) for _ in range(1024)]
        
        # Normalize to unit length (L2 norm = 1)
        norm = math.sqrt(sum(x*x for x in raw_vector))
        return [x/norm for x in raw_vector]
    
    try:
        # Use Ollama for embeddings
        response = ollama.embed(model=EMBEDDING_MODEL, prompt=text)
        
        # Normalize the embedding to unit length
        import math
        raw_vector = response['embedding']
        norm = math.sqrt(sum(x*x for x in raw_vector))
        return [x/norm for x in raw_vector]
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise

# ----------------------
# Search Operations
# ----------------------

def search_memories_vector(
    query_embedding: npt.ArrayLike,
    user_id: Optional[str] = None,
    limit: int = 10,
    similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
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
    results = query_fetchall(query, tuple(params), as_dict=True)
    
    # Ensure similarity scores are float32
    for result in results:
        if 'similarity' in result:
            result['similarity'] = float(result['similarity'])  # Keep as Python float for JSON serialization
    
    return results

def semantic_search(query: str, user_id: Optional[str] = None, limit: int = 10, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
    """Search memories using semantic similarity
    
    Args:
        query: The search query text
        user_id: Optional user ID to filter results
        limit: Maximum number of results
        similarity_threshold: Minimum similarity threshold (-1 to 1 scale, where 1 is identical)
                             Higher values return fewer but more relevant results
        
    Returns:
        List of matching memories with similarity scores
    """
    # Generate embedding for the query (already normalized by generate_embedding)
    query_embedding = generate_embedding(query)
    
    # Perform vector search with normalized vectors
    results = search_memories_vector(
        query_embedding=query_embedding,
        user_id=user_id,
        limit=limit,
        similarity_threshold=similarity_threshold
    )
    
    return results
