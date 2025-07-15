from db_ll_sync import *

from logging_setup import get_logger


logger = get_logger(__name__)


def get_memories_by_uuid(created_by: str, suffix='') -> List:
    query = """
    SELECT id, kind, content, content_hash, content_embedding, _metadata,
           created_by, updated_by
    FROM memories
    WHERE created_by = %s and _deleted_at IS NULL
    """
    if suffix: query += ' ' + suffix
    conn = psycopg.connect(DSN, row_factory=dict_row)
    cursor = conn.cursor()
    cursor.execute(query, (created_by,))
    #print("QQ", query, ((created_by,)))
    for row in cursor:
        #print("ROWWWWWWW RAW", row)
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
    #print("SDSDFDFSG")
    #ret = await query_fetchone(query, (memory_id,), as_dict=True)
    #ret.update(ret.pop('_metadata'))
    #print("SQL", query, (memory_id,))
    cursor.execute(query, (memory_id,))

    ret = cursor.fetchone()

    metadata = ret.pop('_metadata')
    
    ret.update(metadata)

    #print("RET", ret)
    
    #ret.update(ret.pop('_metadata'))
    return ret

def get_edges_by_source(edge_id: str) -> Optional[Dict]:
    conn = psycopg.connect(DSN, row_factory=dict_row)
    cursor = conn.cursor()
    
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
        #print("RET", row['source_id'])
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

    #print("QRY", query)
    #print("EID", edge_id)
    cursor.execute(query, (edge_id,), as_dict=True)
    ret = cursor.fetchone()
    #ret = await query_fetchone(query, (edge_id,), as_dict=True)
    #print("RET", ret)
    if ret:
        ret.update(ret.pop('_metadata'))
        pass
    return ret

def create_memory(
    content: str, 
    user_id: Optional[str] = None,
    kind: Optional[str] = None,
    metadata: Optional[dict] = None,
    content_embedding: Optional[npt.ArrayLike] = None,
    **kw
) -> str: # uuid
    #print("SYNC VERSION", metadata, kw)
    conn = psycopg.connect(DSN)
    cursor = conn.cursor()
    if not content:
        content = ''
        #raise ValueError("Content cannot be empty")
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
    # Prepare parameters
    params = (
        content,
        kind,
        psycopg.types.json.Jsonb(metadata) if metadata else '{}',
        Vector(_ensure_float32(content_embedding).tolist()) if content_embedding is not None else None,
        user_id,
        user_id
    )
    #print("SDFGF", params)
    cursor.execute(query, params)
    record_uuid = cursor.fetchone()[0]
    #print("NEW VERTEX", record_uuid)
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

    # Prepare query and parameters
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

    # Prepare parameters
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
        result = cursor.execute(query, params)
        #result = await query_fetchone(query, params)
        #print("R", (result,))
        result = cursor.fetchone()
        #print("R", (result,))
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


def load_simplified_convo(convo_id):
    return simplify_convo( load_convo(convo_id) )


def simplify_convo(convo):
    """
    turns a complex array of dicts
    into the minumum we need to send to the context window
    """
    for msg in convo:
        kind = msg.get('kind')
        done = msg.get('done', None)
        if kind == 'history':
            #print("MESSAGE")
            #print("H", msg)
            if done is None:
                yield dict(role=msg['role'],
                           content=msg['content'])
            else:
                yield dict(role=msg['role'],
                           content=msg['content'],
                           done=done)
        elif kind == 'session':
            #print("SESSION")
            pass
        else:
            NO_WAY


def load_convo(suid):
    session = get_memory_by_id(suid)
    yield session

    for targets_edge in get_edges_by_target( session['id'] ):
        source_id = targets_edge['source_id']
        vertex = get_memory_by_id(source_id)
        yield vertex


def store_convo(history, title):
    uuid = get_current_user_id()
    suid = create_memory(title, uuid, kind='session')
    for h in history:
        h['user_id'] = uuid
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
