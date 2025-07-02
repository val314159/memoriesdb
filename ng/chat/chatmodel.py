"""
Chat Model for MemoriesDB

Lightweight chat functionality using the graph database with dictionaries.
- Messages are stored as memory vertices
- Message order and relationships are stored as edges
- Sessions are groups of messages with metadata
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
import json

# Import database utilities
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_utils import execute, query_fetchall, query_fetchone, generate_uuid_ossp

# Message roles
USER = "user"
ASSISTANT = "assistant"
SYSTEM = "system"
TOOL = "tool"

async def create_message(content: str, role: str = USER, **metadata) -> Dict[str, Any]:
    """Create a message dictionary with proper structure"""
    return {
        'id': generate_uuid_ossp(),
        'content': content,
        'kind': 'chat_message',
        '_metadata': {
            'role': role,
            'timestamp': datetime.utcnow().isoformat(),
            **metadata
        }
    }

def prepare_message_for_db(message: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Prepare message for database insertion"""
    return {
        'id': message['id'],
        'kind': 'chat_message',
        'content': message['content'],
        '_metadata': json.dumps(message.get('_metadata', {})),
        'created_by': user_id,
        'updated_by': user_id
    }

def format_message_from_db(db_message: Dict[str, Any]) -> Dict[str, Any]:
    """Format message from database record"""
    if isinstance(db_message.get('_metadata'), str):
        db_message['_metadata'] = json.loads(db_message['_metadata'])
    return db_message

async def create_session(user_id: str, title: str = "New Chat") -> str:
    """Create a new chat session and return its ID"""
    session_id = generate_uuid_ossp()
    metadata = {
        'title': title,
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'model': 'default',
        'forked_from': None
    }
    
    await execute("""
        INSERT INTO memories (id, kind, content, _metadata, created_by, updated_by)
        VALUES (%s, 'chat_session', %s, %s, %s, %s)
    """, (
        session_id,
        title,
        json.dumps(metadata),
        user_id,
        user_id
    ))
    
    return session_id

async def add_message(session_id: str, message: Dict[str, Any], user_id: str) -> str:
    """Add a message to a session and return its ID"""
    # Ensure message has required fields
    if 'id' not in message:
        message['id'] = generate_uuid_ossp()
    
    # Insert message
    db_message = prepare_message_for_db(message, user_id)
    await execute("""
        INSERT INTO memories (id, kind, content, _metadata, created_by, updated_by)
        VALUES (%(id)s, %(kind)s, %(content)s, %(_metadata)s, %(created_by)s, %(updated_by)s)
    """, db_message)
    
    # Link message to session
    await execute("""
        INSERT INTO memory_edges (source_id, target_id, relation, _metadata)
        VALUES (%s, %s, 'contains', '{}')
    """, (session_id, message['id']))
    
    # Link to previous message if exists
    last_msg = await get_last_message(session_id)
    if last_msg:
        await execute("""
            INSERT INTO memory_edges (source_id, target_id, relation, _metadata)
            VALUES (%s, %s, 'next', '{}')
        """, (last_msg['id'], message['id']))
    
    # Update session timestamp
    await execute("""
        UPDATE memories 
        SET _metadata = jsonb_set(
            _metadata::jsonb, 
            '{updated_at}', 
            %s::jsonb,
            true
        )
        WHERE id = %s
    """, (f'"{datetime.utcnow().isoformat()}"', session_id))
    
    return message['id']

async def get_messages(session_id: str, limit: int = None, offset: int = 0) -> List[Dict]:
    """Get messages from a session in chronological order"""
    query = """
    WITH RECURSIVE message_chain AS (
        -- Start with the first message in the session
        SELECT m.* 
        FROM memories m
        JOIN memory_edges e ON m.id = e.target_id
        WHERE e.source_id = %s 
        AND e.relation = 'contains'
        AND NOT EXISTS (
            SELECT 1 FROM memory_edges e2 
            WHERE e2.target_id = m.id AND e2.relation = 'next'
        )
        
        UNION ALL
        
        -- Recursively get next messages
        SELECT m.*
        FROM memories m
        JOIN memory_edges e ON m.id = e.target_id
        JOIN message_chain mc ON e.source_id = mc.id
        WHERE e.relation = 'next'
    )
    SELECT * FROM message_chain
    ORDER BY (_metadata->>'timestamp')::timestamptz
    """
    
    if limit is not None:
        query += f" LIMIT {limit}"
    if offset > 0:
        query += f" OFFSET {offset}"
    
    results = await query_fetchall(query, (session_id,))
    return [format_message_from_db(m) for m in results]

async def get_last_message(session_id: str) -> Optional[Dict]:
    """Get the most recent message in a session"""
    query = """
    SELECT m.*
    FROM memories m
    WHERE m.id = (
        SELECT e.target_id
        FROM memory_edges e
        WHERE e.source_id = %s 
        AND e.relation = 'contains'
        AND NOT EXISTS (
            SELECT 1 FROM memory_edges e2 
            WHERE e2.source_id = e.target_id AND e2.relation = 'next'
        )
        LIMIT 1
    )
    """
    result = await query_fetchone(query, (session_id,))
    return format_message_from_db(result) if result else None

async def list_sessions(user_id: str, limit: int = 20, offset: int = 0) -> List[Dict]:
    """List all chat sessions for a user"""
    query = """
    SELECT 
        id as session_id,
        content as title,
        _metadata->>'created_at' as created_at,
        _metadata->>'updated_at' as updated_at
    FROM memories
    WHERE kind = 'chat_session' 
    AND created_by = %s
    AND _deleted_at IS NULL
    ORDER BY (_metadata->>'updated_at')::timestamptz DESC
    LIMIT %s OFFSET %s
    """
    return await query_fetchall(query, (user_id, limit, offset))

async def delete_session(session_id: str, user_id: str) -> bool:
    """
    Soft delete a chat session and its messages
    Returns True if session was found and deleted
    """
    # Check if session exists and belongs to user
    result = await query_fetchone(
        "SELECT 1 FROM memories WHERE id = %s AND created_by = %s AND _deleted_at IS NULL",
        (session_id, user_id)
    )
    if not result:
        return False
    
    # Soft delete the session
    await execute("""
        UPDATE memories 
        SET _deleted_at = NOW()
        WHERE id = %s 
        AND kind = 'chat_session'
    """, (session_id,))
    
    # Soft delete all messages in the session
    await execute("""
        UPDATE memories m
        SET _deleted_at = NOW()
        FROM memory_edges e
        WHERE e.source_id = %s
        AND e.relation = 'contains'
        AND m.id = e.target_id
        AND m.kind = 'chat_message'
    """, (session_id,))
    
    return True

async def fork_session(session_id: str, user_id: str, new_title: str = None) -> Optional[str]:
    """
    Fork a session, copying all messages
    Returns new session ID or None if original not found
    """
    # Get original session
    session = await query_fetchone(
        "SELECT content, _metadata FROM memories WHERE id = %s AND kind = 'chat_session'",
        (session_id,)
    )
    if not session:
        return None
    
    # Create new session
    new_id = generate_uuid_ossp()
    metadata = json.loads(session['_metadata']) if isinstance(session['_metadata'], str) else session['_metadata']
    metadata.update({
        'title': new_title or f"Fork of {session['content']}",
        'forked_from': session_id,
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    })
    
    await execute("""
        INSERT INTO memories (id, kind, content, _metadata, created_by, updated_by)
        VALUES (%s, 'chat_session', %s, %s, %s, %s)
    """, (
        new_id,
        metadata['title'],
        json.dumps(metadata),
        user_id,
        user_id
    ))
    
    # Copy all messages
    messages = await get_messages(session_id)
    for msg in messages:
        await add_message(new_id, msg, user_id)
    
    return new_id

# No need for init_db() as we're using existing tables
