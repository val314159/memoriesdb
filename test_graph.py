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
import json

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'memories'),
    'user': os.getenv('DB_USER', 'memories_user'),
    'password': os.getenv('DB_PASSWORD', 'your_secure_password'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

class GraphDB:
    # Test user IDs
    SYSTEM_USER_ID = '00000000-0000-0000-0000-000000000000'
    TEST_USER_1 = '00000000-0000-0000-0000-000000000001'
    TEST_USER_2 = '00000000-0000-0000-0000-000000000002'
    
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.conn.autocommit = True
        self._create_test_users()
        self.set_current_user(self.TEST_USER_1)  # Default to test user 1
    
    def set_current_user(self, user_id):
        """Set the current user for this session."""
        self.user_id = user_id
        with self.conn.cursor() as cur:
            cur.execute("SET app.current_user_id = %s", (str(user_id),))
    
    def _create_test_users(self):
        """Create test users if they don't exist."""
        with self.conn.cursor() as cur:
            # Create test users if they don't exist
            cur.execute("""
                INSERT INTO users (id, email)
                VALUES 
                    (%s, 'system@example.com'),
                    (%s, 'test1@example.com'),
                    (%s, 'test2@example.com')
                ON CONFLICT (email) DO NOTHING
            """, (self.SYSTEM_USER_ID, self.TEST_USER_1, self.TEST_USER_2))
        
    def create_memories(self, count=10):
        """Create test memories."""
        fake = Faker()
        memories = []
        
        with self.conn.cursor() as cur:
            # Generate memory data
            data = [(str(uuid.uuid4()), 'note', fake.sentence(), 
                    json.dumps({"source": "test"}),  # This will be cast to JSONB
                    self.user_id, self.user_id) 
                   for _ in range(count)]
            
            # Insert memories in bulk
            execute_values(
                cur,
                """
                INSERT INTO memories (id, kind, content, _metadata, created_by, updated_by)
                VALUES %s
                RETURNING id, content
                """,
                data,
                template="(%s, %s, %s, %s, %s::uuid, %s::uuid)",
                fetch=True
            )
            
            # Fetch and return the created memories
            memories = [{"id": row[0], "content": row[1]} for row in cur.fetchall()]
            
        return memories
    
    def create_relationships(self, memories, connections_per_node=2):
        """Create relationships between memories.
        
        Args:
            memories: List of memory dictionaries with 'id' and 'content'
            connections_per_node: Number of connections to create per memory
        """
        if not memories or len(memories) < 2:
            print("Not enough memories to create relationships")
            return []
            
        edges = []
        relation_types = ['related_to', 'references', 'follows', 'contradicts', 'supports']
        
        print(f"Creating relationships for {len(memories)} memories with {connections_per_node} connections each")
        
        with self.conn.cursor() as cur:
            # Create a list of all memory IDs for easy sampling
            memory_ids = [m['id'] for m in memories]
            print(f"Total unique memory IDs: {len(set(memory_ids))}")
            
            for i, memory in enumerate(memories):
                if i % 10 == 0:
                    print(f"Processing memory {i+1}/{len(memories)}")
                
                # Don't connect to self and ensure we don't exceed available memories
                possible_targets = [m for m in memories if m['id'] != memory['id']]
                
                # Make sure we don't try to create more connections than possible
                num_connections = min(connections_per_node, len(possible_targets))
                if num_connections <= 0:
                    print(f"Skipping memory {memory['id']}: No possible targets")
                    continue
                    
                # Randomly select target memories
                targets = random.sample(possible_targets, num_connections)
                
                for target in targets:
                    # Create a more meaningful relationship based on content similarity
                    source_words = set(memory['content'].lower().split())
                    target_words = set(target['content'].lower().split())
                    common_words = source_words.intersection(target_words)
                    
                    # Choose relation type based on content similarity
                    if len(common_words) > 3:
                        relation = 'related_to'
                    else:
                        relation = random.choice(relation_types)
                    
                    # Calculate strength based on word overlap (0.1 to 1.0)
                    strength = min(0.1 + (len(common_words) / 10), 1.0)
                    
                    edge = {
                        'source_id': memory['id'],
                        'target_id': target['id'],
                        'relation': relation,
                        'strength': round(strength, 2),
                        'confidence': round(0.7 + (random.random() * 0.3), 2),  # 0.7 to 1.0
                        'created_by': self.user_id,
                        'updated_by': self.user_id
                    }
                    edges.append(edge)
            
            # Insert edges in bulk if any were created
            if edges:
                print(f"Inserting {len(edges)} edges into memory_edges")
                try:
                    execute_values(
                        cur,
                        """
                        INSERT INTO memory_edges 
                            (source_id, target_id, relation, strength, confidence, created_by, updated_by)
                        VALUES %s
                        ON CONFLICT (source_id, target_id, relation) 
                        DO UPDATE SET 
                            strength = EXCLUDED.strength,
                            confidence = EXCLUDED.confidence,
                            updated_by = EXCLUDED.updated_by,
                            updated_at = NOW()
                        RETURNING id
                        """,
                        [(
                            e['source_id'], e['target_id'], e['relation'], 
                            e['strength'], e['confidence'],
                            e['created_by'], e['updated_by']
                        ) for e in edges],
                        template="(%s::uuid, %s::uuid, %s, %s, %s, %s::uuid, %s::uuid)",
                        fetch=True
                    )
                    print(f"Successfully inserted edges")
                except Exception as e:
                    print(f"Error inserting edges: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("No edges to insert")
        
        print(f"Created {len(edges)} relationships")
        return edges
    
    def cleanup(self):
        """Clean up test data."""
        with self.conn.cursor() as cur:
            # Disable triggers temporarily to avoid RLS issues during cleanup
            cur.execute("SET session_replication_role = 'replica';")
            
            # Clear tables in the correct order to respect foreign key constraints
            cur.execute("""
                TRUNCATE TABLE 
                    embedding_schedule, 
                    vindexing_schedule, 
                    memory_edges, 
                    memories, 
                    audit_log
                CASCADE;
                
                DELETE FROM users 
                WHERE email IN ('system@example.com', 'test1@example.com', 'test2@example.com');
                
                -- Reset sequences if needed
                SELECT setval(pg_get_serial_sequence('audit_log', 'id'), 1, false);
            """)
            
            # Re-enable triggers
            cur.execute("SET session_replication_role = 'origin';")
            
        print("\nCleaned up test data")

def test_queries(db):
    """Run test queries against the database."""
    with db.conn.cursor() as cur:
        # Test basic query
        print("\n=== Memory Statistics ===")
        cur.execute("""
            SELECT 
                COUNT(*) as total_memories,
                COUNT(DISTINCT created_by) as unique_users,
                (SELECT COUNT(*) FROM memory_edges) as total_relationships
            FROM memories
        """)
        stats = cur.fetchone()
        print(f"Total memories: {stats[0]}")
        print(f"Created by {stats[1]} different users")
        print(f"Total relationships: {stats[2]}")
        
        # Get memory distribution by user
        print("\n=== Memory Distribution by User ===")
        cur.execute("""
            SELECT u.email, COUNT(m.id) as memory_count
            FROM users u
            LEFT JOIN memories m ON u.id = m.created_by
            GROUP BY u.email
            ORDER BY memory_count DESC
        """)
        print("\nMemories per user:")
        for email, count in cur.fetchall():
            print(f"- {email}: {count} memories")
        
        # Test graph traversal if we have memories
        cur.execute("SELECT COUNT(*) FROM memories")
        if cur.fetchone()[0] > 0:
            # Get a random memory
            cur.execute("""
                SELECT m.id, m.content, u.email as creator
                FROM memories m
                JOIN users u ON m.created_by = u.id
                ORDER BY random() 
                LIMIT 1
            """)
            memory = cur.fetchone()
            
            if memory:
                memory_id, memory_content, creator = memory
                print(f"\n=== Analyzing Memory ===")
                print(f"Content: {memory_content}")
                print(f"Created by: {creator}")
                
                # Find related memories with details
                print("\n--- Direct Relationships ---")
                cur.execute("""
                    SELECT 
                        m.id,
                        m.content,
                        e.relation,
                        e.strength,
                        e.confidence,
                        u.email as creator
                    FROM memory_edges e
                    JOIN memories m ON e.target_id = m.id
                    JOIN users u ON m.created_by = u.id
                    WHERE e.source_id = %s
                    ORDER BY e.strength DESC, e.confidence DESC
                    LIMIT 5
                """, (memory_id,))
                
                relationships = cur.fetchall()
                if relationships:
                    print(f"Found {len(relationships)} direct relationships:")
                    for rel in relationships:
                        rel_id, content, rel_type, strength, confidence, creator = rel
                        print(f"\n- {content}")
                        print(f"  Type: {rel_type}")
                        print(f"  Strength: {strength:.2f}, Confidence: {confidence:.2f}")
                        print(f"  Created by: {creator}")
                else:
                    print("No direct relationships found.")
                
                # Find incoming relationships
                cur.execute("""
                    SELECT 
                        m.id,
                        m.content,
                        e.relation,
                        e.strength,
                        e.confidence,
                        u.email as creator
                    FROM memory_edges e
                    JOIN memories m ON e.source_id = m.id
                    JOIN users u ON m.created_by = u.id
                    WHERE e.target_id = %s
                    ORDER BY e.strength DESC, e.confidence DESC
                    LIMIT 3
                """, (memory_id,))
                
                incoming = cur.fetchall()
                if incoming:
                    print(f"\n--- Referenced By ({len(incoming)}) ---")
                    for rel in incoming:
                        rel_id, content, rel_type, strength, confidence, creator = rel
                        print(f"\n- {content}")
                        print(f"  Type: {rel_type} (incoming)")
                        print(f"  Strength: {strength:.2f}, Confidence: {confidence:.2f}")
                        print(f"  Created by: {creator}")
                
                # Find 2nd degree connections
                cur.execute("""
                    WITH RECURSIVE graph_search AS (
                        -- Start with our memory
                        SELECT 
                            source_id, 
                            target_id, 
                            relation, 
                            strength, 
                            1 as depth,
                            ARRAY[source_id, target_id] as path
                        FROM memory_edges 
                        WHERE source_id = %s
                        
                        UNION ALL
                        
                        -- Follow edges to depth 2
                        SELECT 
                            e.source_id, 
                            e.target_id, 
                            e.relation, 
                            e.strength * gs.strength as strength,
                            gs.depth + 1,
                            gs.path || e.target_id
                        FROM memory_edges e
                        JOIN graph_search gs ON e.source_id = gs.target_id
                        WHERE gs.depth < 2  -- Limit to 2nd degree
                        AND NOT e.target_id = ANY(gs.path)  -- Avoid cycles
                    )
                    SELECT DISTINCT ON (m.id)
                        m.id,
                        m.content,
                        gs.relation,
                        gs.strength,
                        u.email as creator,
                        gs.depth
                    FROM graph_search gs
                    JOIN memories m ON gs.target_id = m.id
                    JOIN users u ON m.created_by = u.id
                    WHERE gs.target_id != %s  -- Exclude original memory
                    ORDER BY m.id, gs.strength DESC
                    LIMIT 5
                """, (memory_id, memory_id))
                
                second_degree = cur.fetchall()
                if second_degree:
                    print("\n--- Second Degree Connections ---")
                    for rel in second_degree:
                        rel_id, content, rel_type, strength, creator, depth = rel
                        print(f"\n- {content}")
                        print(f"  Type: {rel_type} ({depth}° connection)")
                        print(f"  Strength: {strength:.4f}")
                        print(f"  Created by: {creator}")

def check_database():
    """Check database connection and list tables."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            # List all tables
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cur.fetchall()]
            print("\n=== Database Tables ===")
            for table in tables:
                print(f"- {table}")
                
                # Show table structure
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = %s
                    ORDER BY ordinal_position;
                """, (table,))
                for col_name, data_type in cur.fetchall():
                    print(f"  - {col_name}: {data_type}")
        
        # Check if the memory_edges table exists and has data
        with conn.cursor() as cur:
            if 'memory_edges' in tables:
                cur.execute("SELECT COUNT(*) FROM memory_edges;")
                count = cur.fetchone()[0]
                print(f"\nMemory edges count: {count}")
            else:
                print("\nmemory_edges table does not exist")
                
    except Exception as e:
        print(f"\nError checking database: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    print("\n=== Starting GraphDB Test ===\n")
    check_database()
    
    try:
        db = GraphDB()
        
        # Test with different users
        print("--- Testing with User 1 ---")
        db.set_current_user(db.TEST_USER_1)
        print(f"Creating memories as user {db.user_id}")
        memories = db.create_memories(30)  # Create 30 test memories as user 1
        
        print("\n--- Testing with User 2 ---")
        db.set_current_user(db.TEST_USER_2)
        print(f"Creating memories as user {db.user_id}")
        memories += db.create_memories(30)  # Create 30 more as user 2
        
        # Create relationships between memories
        print("\n--- Creating relationships (this may take a moment) ---")
        db.create_relationships(memories, connections_per_node=5)  # More connections per node
        
        # Run test queries
        test_queries(db)
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        raise
    finally:
        # Clean up
        if 'db' in locals():
            db.cleanup()
        print("\n=== Test Complete ===")
        db.conn.close()

if __name__ == "__main__":
    main()
