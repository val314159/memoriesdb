"""
Memory Graph API for interacting with the PostgreSQL graph database.
"""
import json
import logging
from typing import List, Dict, Any, Optional, Union
from uuid import UUID, uuid4

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryGraph:
    def __init__(self, conn: connection):
        """Initialize with a database connection."""
        self.conn = conn
        self.conn.autocommit = True

    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a query and return results as dicts."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(query, params or ())
                if cur.description:
                    return [dict(row) for row in cur.fetchall()]
                return []
            except Exception as e:
                logger.error(f"Error executing query: {e}")
                raise

    # Core CRUD Operations
    def create_memory(self, content: str, metadata: Optional[Dict] = None, 
                     content_embedding: Optional[List[float]] = None) -> Dict:
        """Create a new memory node.
        
        Args:
            content: The text content of the memory
            metadata: Optional metadata as a dictionary
            content_embedding: Optional vector embedding for semantic search
            
        Returns:
            The created memory record
        """
        query = """
            INSERT INTO memories (content, content_hash, content_embedding, _metadata)
            VALUES (
                %s, 
                digest(%s, 'sha256'),
                %s,
                %s
            )
            RETURNING *
        """
        metadata = metadata or {}
        result = self.execute(
            query, 
            (
                content,
                content,  # For hash generation
                content_embedding,
                json.dumps(metadata)
            )
        )
        return result[0] if result else None

    def create_edge(self, source_id: UUID, target_id: UUID, relation: str, metadata: Optional[Dict] = None) -> Dict:
        """Create a relationship between two memories."""
        query = """
            INSERT INTO memory_edges (source_id, target_id, relation, _metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING *
        """
        result = self.execute(query, (source_id, target_id, relation, json.dumps(metadata or {})))
        return result[0] if result else None

    # Session Management
    def create_session(self, title: str, metadata: Optional[Dict] = None) -> Dict:
        """Create a new chat session."""
        # Create the session memory
        session_mem = self.create_memory(
            title,
            {"title": title, "type": "session", **(metadata or {})}
        )
        
        # Link it to the session type
        session_type = self.get_memory_by_content("session")
        if not session_type:
            raise ValueError("Session type not found in database")
            
        self.create_edge(session_mem['id'], session_type['id'], 'has_type')
        return session_mem

    def fork_session(self, session_id: UUID, title: Optional[str] = None) -> Dict:
        """Fork an existing session."""
        # Create new session
        orig_session = self.get_memory(session_id)
        if not orig_session:
            raise ValueError("Original session not found")
            
        new_title = title or f"Fork of {orig_session['content']}"
        new_session = self.create_session(new_title, {"forked_from": str(session_id)})
        
        # Create fork relationship
        self.create_edge(new_session['id'], session_id, 'forked_from')
        return new_session

    # Query Methods
    def update_memory(self, memory_id: UUID, content: str = None, 
                     metadata: Dict = None, content_embedding: List[float] = None) -> Optional[Dict]:
        """Update an existing memory.
        
        Args:
            memory_id: ID of the memory to update
            content: New content (if updating)
            metadata: New metadata (will be merged with existing)
            content_embedding: New vector embedding
            
        Returns:
            Updated memory record or None if not found
        """
        updates = []
        params = []
        
        if content is not None:
            updates.append("content = %s")
            params.append(content)
            # Update hash when content changes
            updates.append("content_hash = digest(%s, 'sha256')")
            params.append(content)
            
        if content_embedding is not None:
            updates.append("content_embedding = %s")
            params.append(content_embedding)
            
        if metadata is not None:
            # Merge with existing metadata
            updates.append("_metadata = _metadata || %s")
            params.append(json.dumps(metadata))
            
        if not updates:
            return self.get_memory(memory_id)
            
        params.append(memory_id)
        set_clause = ", ".join(updates)
        
        query = f"""
            UPDATE memories 
            SET {set_clause}, _updated_at = NOW()
            WHERE id = %s
            RETURNING *
        """
        
        result = self.execute(query, params)
        return result[0] if result else None
        
    def get_memory(self, memory_id: UUID) -> Optional[Dict]:
        """Get a memory by ID."""
        result = self.execute("SELECT * FROM memories WHERE id = %s", (memory_id,))
        return result[0] if result else None

    def get_memory_by_content(self, content: str) -> Optional[Dict]:
        """Get a memory by its exact content."""
        result = self.execute("SELECT * FROM memories WHERE content = %s", (content,))
        return result[0] if result else None

    def get_session_messages(self, session_id: UUID) -> List[Dict]:
        """Get all messages in a session, including forked messages."""
        query = """
            SELECT * FROM get_session_messages(%s)
            ORDER BY position
        """
        return self.execute(query, (session_id,))

    def add_message(self, session_id: UUID, role: str, content: str, **metadata) -> Dict:
        """Add a message to a session."""
        # Create message
        msg_metadata = {"role": role, "position": self._get_next_position(session_id), **metadata}
        message = self.create_memory(content, msg_metadata)
        
        # Link to message type
        message_type = self.get_memory_by_content("message") or \
                      self.create_memory("message", {"type": "message"})
        self.create_edge(message['id'], message_type['id'], 'has_type')
        
        # Link to session
        self.create_edge(message['id'], session_id, 'belongs_to')
        return message

    def _get_next_position(self, session_id: UUID) -> int:
        """Get the next position number for a message in the session."""
        query = """
            SELECT MAX((_metadata->>'position')::int) as max_pos
            FROM memories m
            JOIN memory_edges e ON m.id = e.source_id
            WHERE e.target_id = %s AND e.relation = 'belongs_to'
        """
        result = self.execute(query, (session_id,))
        return (result[0]['max_pos'] or 0) + 1 if result else 1

    # Search
    def search_memories(self, query: str, limit: int = 10) -> List[Dict]:
        """Search memories by content (simple text search)."""
        query = """
            SELECT * FROM memories 
            WHERE content ILIKE %s
            ORDER BY _created_at DESC
            LIMIT %s
        """
        return self.execute(query, (f"%{query}%", limit))

    def semantic_search(self, query_embedding: List[float], limit: int = 5) -> List[Dict]:
        """Find similar memories using vector similarity."""
        query = """
            SELECT id, content, 
                   content_embedding <=> %s as distance
            FROM memories
            WHERE content_embedding IS NOT NULL
            ORDER BY distance
            LIMIT %s
        """
        return self.execute(query, (query_embedding, limit))

    # Cleanup
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    # Context manager support
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Helper function to create a connection
def connect_db(connection_string: str = None, **kwargs) -> MemoryGraph:
    """Create a new database connection."""
    if not connection_string and not kwargs:
        kwargs = {
            'dbname': 'memoriesdb',
            'user': 'postgres',
            'password': 'postgres',
            'host': 'localhost',
            'port': '5432'
        }
    
    conn = psycopg2.connect(connection_string or "", **kwargs)
    return MemoryGraph(conn)
