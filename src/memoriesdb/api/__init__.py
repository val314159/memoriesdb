import os
import psycopg2
from typing import Optional, Dict, Any, List
from pgvector.psycopg2 import register_vector
from psycopg2 import extensions as ext
from .memory_graph import MemoryGraph

def _register_vector_adapters(conn):
    """Register adapters for vector types with psycopg2."""
    # Register vector type adapter
    class VectorAdapter:
        def __init__(self, vector):
            self.vector = vector
        
        def getquoted(self):
            # Convert list to PostgreSQL array syntax
            if isinstance(self.vector, (list, tuple)):
                return (b'[' + ",".join(str(float(x)) for x in self.vector).encode() + b"']::vector").replace(b"''", b"'")
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

def connect(connection_string: Optional[str] = None, **kwargs) -> MemoryGraph:
    """Create a new MemoryGraph connection.
    
    Args:
        connection_string: PostgreSQL connection string (optional)
        **kwargs: Connection parameters (host, dbname, user, password, port)
        
    Returns:
        MemoryGraph: A new MemoryGraph instance
        
    Example:
        # Using environment variables
        db = connect()
        
        # Using connection string
        db = connect("postgresql://user:pass@host:port/dbname")
        
        # Using keyword arguments
        db = connect(host='localhost', dbname='mydb', user='postgres')
    """
    if not connection_string and not kwargs:
        kwargs = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'dbname': os.getenv('POSTGRES_DB', 'memories'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD'),
            'port': os.getenv('POSTGRES_PORT', '5432')
        }
    
    # Create connection and set autocommit before creating MemoryGraph
    conn = psycopg2.connect(connection_string or "", **kwargs)
    conn.autocommit = True  # Set autocommit before any operations
    register_vector(conn)
    _register_vector_adapters(conn)
    return MemoryGraph(conn)
