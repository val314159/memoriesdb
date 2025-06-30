#!/usr/bin/env python3
"""
Test script for the MemoriesDB graph database.
Focuses on core functionality: creating memories, connecting them, and querying the graph.
"""
import os
import uuid
import random
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from faker import Faker

# Load environment variables
load_dotenv()

# Configuration
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'memories'),
    'user': os.getenv('DB_USER', 'memories_user'),
    'password': os.getenv('DB_PASSWORD', 'your_secure_password'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

# Initialize Faker
fake = Faker()

class GraphDB:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.conn.autocommit = True
        self.user_id = self._get_or_create_user()
        # Set the current user for this connection
        self._ensure_session_variables()
    
    def _ensure_session_variables(self):
        """Ensure all required session variables are set."""
        with self.conn.cursor() as cur:
            # Set a default user ID if not set
            cur.execute("""
                DO $$
                BEGIN
                    -- Set a default value if not already set
                    IF current_setting('app.current_user_id', true) IS NULL THEN
                        PERFORM set_config('app.current_user_id', '00000000-0000-0000-0000-000000000000', true);
                    END IF;
                EXCEPTION WHEN undefined_object THEN
                    -- Parameter doesn't exist yet, create it
                    PERFORM set_config('app.current_user_id', '00000000-0000-0000-0000-000000000000', true);
                END $$;
            """)
            # Now set the actual user ID
            self._set_current_user()
        
    def _set_current_user(self):
        """Set the current user in the session for audit triggers."""
        with self.conn.cursor() as cur:
            # Set the session variable for this connection
            # The 'true' parameter makes it persist for the session
            cur.execute("SET app.current_user_id = %s", (str(self.user_id),))
        
    def _get_or_create_user(self):
        """Get or create a test user."""
        with self.conn.cursor() as cur:
            # Try to get existing test user
            cur.execute("""
                INSERT INTO users (email) 
                VALUES ('test@example.com')
                ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
                RETURNING id;
            """)
            return cur.fetchone()[0]
    
    def create_memories(self, count=10):
        """Create test memories."""
        memories = []
        for _ in range(count):
            memory = {
                'id': str(uuid.uuid4()),
                'content': fake.sentence(),
                'kind': random.choice(['note', 'idea', 'task', 'reference']),
                'created_by': self.user_id,
                'updated_by': self.user_id
            }
            memories.append(memory)
        
        with self.conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO memories (id, content, kind, created_by, updated_by)
                VALUES %s
                RETURNING id;
                """,
                [(m['id'], m['content'], m['kind'], m['created_by'], m['updated_by']) 
                 for m in memories],
                page_size=100
            )
        
        print(f"Created {len(memories)} memories")
        return memories
    
    def create_relationships(self, memories, max_connections=3):
        """Create random relationships between memories."""
        edges = []
        relations = ['references', 'related_to', 'similar_to', 'follows']
        
        for source in memories:
            # Connect to 1-3 random memories
            targets = random.sample(memories, min(max_connections, len(memories)))
            for target in targets:
                if source['id'] != target['id']:  # No self-references
                    edges.append({
                        'source_id': source['id'],
                        'target_id': target['id'],
                        'relation': random.choice(relations),
                        'strength': round(random.uniform(0.1, 1.0), 2),
                        'confidence': round(random.uniform(0.5, 1.0), 2),
                        'created_by': self.user_id,
                        'updated_by': self.user_id
                    })
        
        with self.conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO memory_edges 
                    (source_id, target_id, relation, strength, confidence, created_by, updated_by)
                VALUES %s
                ON CONFLICT (source_id, target_id, relation) DO NOTHING;
                """,
                [(e['source_id'], e['target_id'], e['relation'], e['strength'], 
                  e['confidence'], e['created_by'], e['updated_by']) 
                 for e in edges],
                page_size=100
            )
        
        print(f"Created {len(edges)} relationships")
        return edges
    
    def test_queries(self):
        """Run test queries to verify functionality."""
        with self.conn.cursor() as cur:
            # 1. Basic memory retrieval
            print("\n--- Basic Memory Retrieval ---")
            cur.execute("""
                SELECT id, content, kind 
                FROM memories 
                LIMIT 5;
            """)
            print("Sample memories:")
            for row in cur.fetchall():
                print(f"- {row[1]} ({row[2]})")
            
            # 2. Test the compound index (relation + strength + confidence)
            print("\n--- Testing Compound Index ---")
            cur.execute("""
                EXPLAIN ANALYZE 
                SELECT source_id, target_id, relation, strength, confidence
                FROM memory_edges
                WHERE relation = 'references' AND strength > 0.7
                ORDER BY confidence DESC
                LIMIT 5;
            """)
            print("\nQuery plan for relation + strength + confidence:")
            for row in cur.fetchall():
                print(row[0])
            
            # 3. Test graph traversal
            print("\n--- Testing Graph Traversal ---")
            cur.execute("""
                WITH RECURSIVE graph_search AS (
                    SELECT id, content, 1 as depth
                    FROM memories 
                    WHERE id IN (
                        SELECT id FROM memories LIMIT 1  -- Start with a random memory
                    )
                    
                    UNION ALL
                    
                    SELECT m.id, m.content, gs.depth + 1
                    FROM memories m
                    JOIN memory_edges e ON m.id = e.target_id
                    JOIN graph_search gs ON e.source_id = gs.id
                    WHERE gs.depth < 3  -- Limit depth
                )
                SELECT depth, content FROM graph_search LIMIT 5;
            """)
            print("\nSample graph traversal (first 5 nodes):")
            for depth, content in cur.fetchall():
                print(f"Depth {depth}: {content}")
    
    def cleanup(self):
        """Clean up test data."""
        with self.conn.cursor() as cur:
            cur.execute("""
                DELETE FROM memory_edges;
                DELETE FROM memories;
                DELETE FROM users WHERE email = 'test@example.com';
            """)
        print("\nCleaned up test data")

def main():
    print("=== Starting GraphDB Test ===")
    db = GraphDB()
    
    try:
        # Create test data
        print("\n--- Creating Test Data ---")
        memories = db.create_memories(20)  # Create 20 test memories
        db.create_relationships(memories)  # Create random relationships
        
        # Run test queries
        print("\n--- Running Test Queries ---")
        db.test_queries()
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        raise
    finally:
        # Uncomment to clean up after testing
        # db.cleanup()
        db.conn.close()

if __name__ == "__main__":
    main()
