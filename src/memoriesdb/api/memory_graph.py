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
        if content_embedding is not None:
            # Convert the list to a string representation for SQL
            vector_str = '[' + ','.join(str(float(x)) for x in content_embedding) + ']'
            query = """
                INSERT INTO memories (content, content_hash, content_embedding, _metadata)
                VALUES (
                    %s, 
                    digest(%s, 'sha256'),
                    %s::vector,
                    %s
                )
                RETURNING *
            """
            params = (content, content, vector_str, json.dumps(metadata or {}))
        else:
            query = """
                INSERT INTO memories (content, content_hash, _metadata)
                VALUES (
                    %s, 
                    digest(%s, 'sha256'),
                    %s
                )
                RETURNING *
            """
            params = (content, content, json.dumps(metadata or {}))
            
        result = self.execute(query, params)
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
        
        # Link it to the session type (using the known ID from the initialization script)
        session_type_id = UUID('00000000-0000-4000-8000-000000000104')
        session_type = self.get_memory(session_type_id)
        if not session_type:
            # Fallback to content-based lookup if the ID doesn't exist
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
        # Convert UUID to string if it's a UUID object
        memory_id_str = str(memory_id) if hasattr(memory_id, 'hex') else memory_id
        result = self.execute("SELECT * FROM memories WHERE id = %s", (memory_id_str,))
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
            SELECT MAX((m._metadata->>'position')::int) as max_pos
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
        """Find similar memories using vector similarity.
        
        Args:
            query_embedding: The query vector as a list of floats
            limit: Maximum number of results to return
            
        Returns:
            List of dictionaries containing memory id, content, and distance
        """
        # Convert the list to a string representation that pgvector can understand
        vector_str = '[' + ','.join(str(float(x)) for x in query_embedding) + ']'
        
        # Use string formatting for the vector since psycopg2 doesn't have a built-in vector type
        query = f"""
            SELECT id, content, 
                   content_embedding <=> '{vector_str}'::vector as distance
            FROM memories
            WHERE content_embedding IS NOT NULL
            ORDER BY distance
            LIMIT %s
        """
        return self.execute(query, (limit,))

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


def register_vector_adapters(conn):
    """Register adapters for vector types."""
    from psycopg2 import extensions as ext
    
    # Register UUID type
    import uuid
    ext.register_uuid()
    
    # Register vector type adapter
    class VectorAdapter:
        def __init__(self, vector):
            self.vector = vector
        
        def getquoted(self):
            # Convert list to PostgreSQL array syntax
            if isinstance(self.vector, (list, tuple)):
                return b"'[" + ",".join(str(float(x)) for x in self.vector).encode() + b"]'::vector"
            return str(self.vector).encode()
    
    def cast_vector(value, cur):
        if value is None:
            return None
        # Parse the vector string into a list of floats
        return [float(x) for x in value[1:-1].split(',')] if value.startswith('[') else value
    
    # Register the adapter for lists/tuples to be converted to vectors
    ext.register_adapter(list, VectorAdapter)
    ext.register_adapter(tuple, VectorAdapter)
    
    # Register the type caster for vectors coming from the database
    VECTOR_OID = 600  # Default OID for vector type in pgvector
    VECTOR = ext.new_type((VECTOR_OID,), "VECTOR", cast_vector)
    ext.register_type(VECTOR, conn)

# Helper function to create a connection
def connect_db(connection_string: str = None, **kwargs) -> MemoryGraph:
    """Create a new database connection.
    
    Args:
        connection_string: PostgreSQL connection string
        **kwargs: Additional connection parameters
        
    Returns:
        MemoryGraph: A new MemoryGraph instance
    """
    if not connection_string and not kwargs:
        kwargs = {
            'dbname': 'memories',
            'user': 'postgres',
            'password': 'pencil',
            'host': 'localhost',
            'port': '5432'
        }
    conn = psycopg2.connect(connection_string or "", **kwargs)
    
    # Register custom type adapters
    register_vector_adapters(conn)
    
    return MemoryGraph(conn)
