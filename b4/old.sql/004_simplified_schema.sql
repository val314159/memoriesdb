-- Enable required extensions if not already enabled in 000_init.sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Drop existing tables if they exist (for idempotent migrations)
DROP TRIGGER IF EXISTS update_memories_timestamp ON memories;
DROP TRIGGER IF EXISTS refresh_memory_graph_trigger ON memories;
DROP TRIGGER IF EXISTS refresh_memory_edges_graph_trigger ON memory_edges;

DROP FUNCTION IF EXISTS update_modified_column();
DROP FUNCTION IF EXISTS refresh_memory_graph();

DROP MATERIALIZED VIEW IF EXISTS memory_graph;
DROP TABLE IF EXISTS memory_edges CASCADE;
DROP TABLE IF EXISTS memories CASCADE;

-- Core memories table
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v1mc(),
    _created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _deleted_at TIMESTAMPTZ,
    content TEXT,
    content_hash BYTEA,  -- For change detection and deduplication
    content_embedding VECTOR(1024),
    _metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT unique_content_hash UNIQUE(content_hash)  -- Optional: Enable if you want to prevent duplicate content
);

-- Edge table for all relationships
CREATE TABLE memory_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v1mc(),
    _created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    relation VARCHAR(64) NOT NULL,  -- e.g., 'parent_of', 'has_type', 'has_role'
    weight FLOAT DEFAULT 1.0,
    _metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(source_id, target_id, relation)
);

-- Indexes for performance
CREATE INDEX idx_memories_created ON memories(_created_at);
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (content_embedding vector_cosine_ops);
CREATE INDEX idx_memory_edges_source ON memory_edges(source_id);
CREATE INDEX idx_memory_edges_target ON memory_edges(target_id);
CREATE INDEX idx_memory_edges_relation ON memory_edges(relation);

-- Function to generate content hash
CREATE OR REPLACE FUNCTION generate_content_hash(content TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN digest(coalesce(content, ''), 'sha256');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to update timestamps and content hash
CREATE OR REPLACE FUNCTION update_memory_fields() 
RETURNS TRIGGER AS $$
BEGIN
    NEW._updated_at = NOW();
    IF NEW.content IS DISTINCT FROM OLD.content THEN
        NEW.content_hash = generate_content_hash(NEW.content);
    END IF;
    RETURN NEW; 
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic updates
CREATE TRIGGER update_memory_fields_trigger
BEFORE UPDATE ON memories
FOR EACH ROW EXECUTE FUNCTION update_memory_fields();

-- Trigger to set content_hash on insert
CREATE TRIGGER set_content_hash_on_insert
BEFORE INSERT ON memories
FOR EACH ROW
WHEN (NEW.content_hash IS NULL)
EXECUTE FUNCTION set_content_hash();

-- Create a function to set content_hash on insert
CREATE OR REPLACE FUNCTION set_content_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.content_hash = generate_content_hash(NEW.content);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Materialized view for common graph queries
CREATE MATERIALIZED VIEW memory_graph AS
SELECT 
    m.id, m.content,
    jsonb_build_object(
        'incoming', (
            SELECT jsonb_agg(jsonb_build_object(
                'id', e.id,
                'relation', e.relation,
                'source', e.source_id
            ))
            FROM memory_edges e 
            WHERE e.target_id = m.id
        ),
        'outgoing', (
            SELECT jsonb_agg(jsonb_build_object(
                'id', e.id,
                'relation', e.relation,
                'target', e.target_id
            ))
            FROM memory_edges e 
            WHERE e.source_id = m.id
        )
    ) as relationships
FROM memories m
WHERE m._deleted_at IS NULL;

-- Refresh function for the materialized view
CREATE OR REPLACE FUNCTION refresh_memory_graph()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY memory_graph;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Triggers to keep the materialized view updated
CREATE TRIGGER refresh_memory_graph_trigger
AFTER INSERT OR UPDATE OR DELETE ON memories
FOR EACH STATEMENT EXECUTE FUNCTION refresh_memory_graph();

CREATE TRIGGER refresh_memory_edges_graph_trigger
AFTER INSERT OR UPDATE OR DELETE ON memory_edges
FOR EACH STATEMENT EXECUTE FUNCTION refresh_memory_graph();

-- Add comments for documentation
COMMENT ON TABLE memories IS 'Core table for storing memory nodes';
COMMENT ON TABLE memory_edges IS 'Relationships between memory nodes';
COMMENT ON COLUMN memory_edges.relation IS 'Type of relationship between source and target memories';
COMMENT ON MATERIALIZED VIEW memory_graph IS 'Pre-computed graph view of memory relationships';

-- Initialize system categories
INSERT INTO memories (id, content) VALUES 
    -- System categories
    ('00000000-0000-4000-8000-000000000100', 'system'),
    ('00000000-0000-4000-8000-000000000101', 'category'),
    ('00000000-0000-4000-8000-000000000102', 'user'),
    ('00000000-0000-4000-8000-000000000103', 'role'),
    
    -- Common relations
    ('00000000-0000-4000-8000-000000000201', 'parent_of'),
    ('00000000-0000-4000-8000-000000000202', 'has_type'),
    ('00000000-0000-4000-8000-000000000203', 'has_role'),
    ('00000000-0000-4000-8000-000000000204', 'related_to'),
    ('00000000-0000-4000-8000-000000000205', 'belongs_to'),
    
    -- System roles
    ('00000000-0000-4000-8000-000000000301', 'assistant'),
    ('00000000-0000-4000-8000-000000000302', 'tool'),
    ('00000000-0000-4000-8000-000000000303', 'admin'),
    ('00000000-0000-4000-8000-000000000304', 'user');

-- Set up category relationships
INSERT INTO memory_edges (source_id, target_id, relation) VALUES
    -- System categories
    ('00000000-0000-4000-8000-000000000101', '00000000-0000-4000-8000-000000000100', 'belongs_to'),  -- category is a system type
    ('00000000-0000-4000-8000-000000000102', '00000000-0000-4000-8000-000000000101', 'belongs_to'),  -- user is a category
    ('00000000-0000-4000-8000-000000000103', '00000000-0000-4000-8000-000000000101', 'belongs_to'),  -- role is a category
    
    -- Categorize the system roles
    ('00000000-0000-4000-8000-000000000301', '00000000-0000-4000-8000-000000000103', 'has_type'),  -- assistant is a role
    ('00000000-0000-4000-8000-000000000302', '00000000-0000-4000-8000-000000000103', 'has_type'),  -- tool is a role
    ('00000000-0000-4000-8000-000000000303', '00000000-0000-4000-8000-000000000103', 'has_type'),  -- admin is a role
    ('00000000-0000-4000-8000-000000000304', '00000000-0000-4000-8000-000000000103', 'has_type');  -- user is a role

-- Create an example user with admin role
INSERT INTO memories (id, content) VALUES 
    ('00000000-0000-4000-8000-000000004001', 'admin_user');
    
-- Assign roles to the example user
INSERT INTO memory_edges (source_id, target_id, relation) VALUES
    ('00000000-0000-4000-8000-000000004001', '00000000-0000-4000-8000-000000000303', 'has_role'),  -- admin role
    ('00000000-0000-4000-8000-000000004001', '00000000-0000-4000-8000-000000000102', 'has_type');  -- user type

-- Create an example conversation
WITH new_session AS (
    INSERT INTO memories (id, content, _metadata) VALUES 
        ('00000000-0000-4000-8000-000000005001', 'Example Chat Session', '{"title":"First Chat"}'::jsonb)
    RETURNING id
),
session_type AS (
    SELECT id FROM memories WHERE content = 'session' LIMIT 1
)
INSERT INTO memory_edges (source_id, target_id, relation)
SELECT 
    (SELECT id FROM new_session),
    (SELECT id FROM session_type),
    'has_type';

-- Create example messages in the conversation
INSERT INTO memories (id, content, _metadata) VALUES
    ('00000000-0000-4000-8000-000000005101', 
     'You are a helpful assistant.',
     '{"position": 1, "role": "system"}'),
    
    ('00000000-0000-4000-8000-000000005102', 
     'Hello, how are you?',
     '{"position": 2, "role": "user"}'),
    
    ('00000000-0000-4000-8000-000000005103', 
     'I''m doing well, thank you! How can I help you today?',
     '{"position": 3, "role": "assistant"}');

-- Link messages to session and set their types
INSERT INTO memory_edges (source_id, target_id, relation) 
VALUES
    -- Link messages to session
    ('00000000-0000-4000-8000-000000005101', '00000000-0000-4000-8000-000000005001', 'belongs_to'),
    ('00000000-0000-4000-8000-000000005102', '00000000-0000-4000-8000-000000005001', 'belongs_to'),
    ('00000000-0000-4000-8000-000000005103', '00000000-0000-4000-8000-000000005001', 'belongs_to'),
    
    -- Set message types
    ('00000000-0000-4000-8000-000000005101', (SELECT id FROM memories WHERE content = 'message' LIMIT 1), 'has_type'),
    ('00000000-0000-4000-8000-000000005102', (SELECT id FROM memories WHERE content = 'message' LIMIT 1), 'has_type'),
    ('00000000-0000-4000-8000-000000005103', (SELECT id FROM memories WHERE content = 'message' LIMIT 1), 'has_type');

-- Create a forked session (simplified approach)
WITH new_session AS (
    INSERT INTO memories (id, content, _metadata) 
    VALUES (
        '00000000-0000-4000-8000-000000005002', 
        'Forked Chat Session',
        '{"title": "Forked Chat"}'::jsonb
    )
    RETURNING id
),
session_type AS (SELECT id FROM memories WHERE content = 'session' LIMIT 1)
-- Link new session to session type
INSERT INTO memory_edges (source_id, target_id, relation, _metadata)
SELECT 
    (SELECT id FROM new_session),
    (SELECT id FROM session_type),
    'has_type',
    '{}'::jsonb;

-- Create fork relationship between sessions
INSERT INTO memory_edges (source_id, target_id, relation, _metadata)
VALUES (
    '00000000-0000-4000-8000-000000005002',  -- New session
    '00000000-0000-4000-8000-000000005001',  -- Original session
    'forked_from',
    jsonb_build_object('forked_at', NOW())
);

-- Function to get all messages in a session (including forked sessions)
CREATE OR REPLACE FUNCTION get_session_messages(session_id UUID)
RETURNS TABLE (
    message_id UUID,
    content TEXT,
    role TEXT,
    fork_depth INTEGER,
    position INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE session_tree AS (
        SELECT id, 0 as depth
        FROM memories 
        WHERE id = session_id
        
        UNION ALL
        
        SELECT e.target_id, st.depth + 1
        FROM memory_edges e
        JOIN session_tree st ON e.source_id = st.id
        WHERE e.relation = 'forked_from'
    )
    SELECT 
        m.id,
        m.content,
        m._metadata->>'role',
        st.depth,
        (m._metadata->>'position')::int
    FROM memories m
    JOIN memory_edges e ON m.id = e.source_id
    JOIN session_tree st ON e.target_id = st.id
    WHERE e.relation = 'belongs_to'
    ORDER BY (m._metadata->>'position')::int;
END;
$$ LANGUAGE plpgsql STABLE;

/*
-- Example usage:
SELECT * FROM get_session_messages('00000000-0000-4000-8000-000000005002');

-- Enhanced conversation flow with fork visualization:
WITH messages AS (
    SELECT 
        *,
        array_to_string(
            array(
                SELECT content 
                FROM memories 
                WHERE id = ANY(fork_chain[1:array_length(fork_chain, 1)-1])
                ORDER BY array_position(fork_chain, id) DESC
            ), 
            ' → '
        ) as fork_path
    FROM get_session_messages('00000000-0000-4000-8000-000000005002')
)
SELECT 
    CONCAT(role, ': ') as speaker,
    content as message,
    CASE 
        WHEN fork_depth > 0 THEN CONCAT('(from: ', fork_path, ')')
        ELSE '' 
    END as fork_info,
    session_id  -- For UI to track message sources
FROM messages
ORDER BY position;

-- For UI components that need to build a fork tree:
SELECT DISTINCT
    session_id,
    fork_chain,
    (SELECT content FROM memories WHERE id = session_id) as session_name
FROM get_session_messages('00000000-0000-4000-8000-000000005002')
ORDER BY array_length(fork_chain, 1), fork_chain;
*/
