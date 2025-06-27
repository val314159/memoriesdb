-- Drop existing objects if they exist
DROP TRIGGER IF EXISTS update_memories_timestamp ON memories;
DROP TRIGGER IF EXISTS refresh_memory_graph_trigger ON memories;
DROP TRIGGER IF EXISTS refresh_memory_edges_graph_trigger ON memory_edges;

DROP FUNCTION IF EXISTS update_modified_column();
DROP FUNCTION IF EXISTS refresh_memory_graph();

DROP MATERIALIZED VIEW IF EXISTS memory_graph;
DROP TABLE IF EXISTS memory_edges CASCADE;
DROP TABLE IF EXISTS memories CASCADE;
DROP TABLE IF EXISTS audit_log CASCADE;

-- Audit log table
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    record_id UUID NOT NULL,
    operation TEXT NOT NULL,
    operation_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    old_values JSONB,
    new_values JSONB,
    changed_by TEXT DEFAULT current_user
);

-- Core memories table
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v1mc(),
    _created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _deleted_at TIMESTAMPTZ,
    content TEXT,
    content_hash BYTEA,
    content_embedding VECTOR(1024),
    _metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by TEXT DEFAULT current_user,
    updated_by TEXT DEFAULT current_user,
    CONSTRAINT unique_content_hash UNIQUE(content_hash),
    CONSTRAINT content_not_empty CHECK (content IS NULL OR content != '')
);

-- Edge table for all relationships
CREATE TABLE memory_edges (
    id UUID DEFAULT uuid_generate_v1mc(),
    _created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_id UUID NOT NULL,
    target_id UUID NOT NULL,
    relation TEXT NOT NULL CHECK (relation ~ '^[a-z_]+$'),  -- Simple snake_case validation
    weight FLOAT DEFAULT 1.0,
    _metadata JSONB DEFAULT '{}'::jsonb,
    created_by TEXT DEFAULT current_user,
    CONSTRAINT fk_source_memory FOREIGN KEY (source_id) REFERENCES memories(id) ON DELETE CASCADE,
    CONSTRAINT fk_target_memory FOREIGN KEY (target_id) REFERENCES memories(id) ON DELETE CASCADE,
    CONSTRAINT no_self_reference CHECK (source_id != target_id),
    PRIMARY KEY (id),
    CONSTRAINT memory_edges_source_target_relation_key UNIQUE (source_id, target_id, relation)
);

-- Indexes for performance
CREATE INDEX idx_memories_created ON memories(_created_at);
CREATE INDEX idx_memories_updated ON memories(_updated_at);
CREATE INDEX idx_memories_content_gin ON memories USING GIN (to_tsvector('english', content));
CREATE INDEX idx_memories_metadata_gin ON memories USING GIN (_metadata);
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (content_embedding vector_cosine_ops);

CREATE INDEX idx_memory_edges_source ON memory_edges(source_id);
CREATE INDEX idx_memory_edges_target ON memory_edges(target_id);
CREATE INDEX idx_memory_edges_relation ON memory_edges(relation);
CREATE INDEX idx_memory_edges_created ON memory_edges(_created_at);
CREATE INDEX idx_memory_edges_metadata_gin ON memory_edges USING GIN (_metadata);

-- Materialized view for graph traversal optimization
CREATE MATERIALIZED VIEW memory_graph AS
WITH RECURSIVE graph_search AS (
    -- Base case: all nodes
    SELECT 
        id, 
        content, 
        _metadata,
        ARRAY[id] AS path,
        FALSE AS is_cycle,
        0 AS depth
    FROM memories
    
    UNION ALL
    
    -- Recursive case: follow edges
    SELECT 
        m.id,
        m.content,
        m._metadata,
        gs.path || m.id,
        m.id = ANY(gs.path),
        gs.depth + 1
    FROM memories m
    JOIN memory_edges e ON m.id = e.target_id
    JOIN graph_search gs ON e.source_id = gs.id
    WHERE NOT gs.is_cycle
    AND gs.depth < 100  -- Prevent infinite recursion
)
SELECT * FROM graph_search;

-- Function to refresh the materialized view
CREATE OR REPLACE FUNCTION refresh_memory_graph()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY memory_graph;
    RETURN NULL;
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Error refreshing materialized view: %', SQLERRM;
        RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for automatic refresh
CREATE TRIGGER refresh_memory_graph_trigger
AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON memories
FOR EACH STATEMENT
EXECUTE FUNCTION refresh_memory_graph();

CREATE TRIGGER refresh_memory_edges_graph_trigger
AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON memory_edges
FOR EACH STATEMENT
EXECUTE FUNCTION refresh_memory_graph();

-- Full-text search function
CREATE OR REPLACE FUNCTION search_memories(search_term TEXT)
RETURNS TABLE (id UUID, content TEXT, rank FLOAT) AS $$
BEGIN
    RETURN QUERY
    SELECT m.id, m.content, ts_rank(
        to_tsvector('english', m.content),
        plainto_tsquery('english', search_term)
    ) as rank
    FROM memories m
    WHERE to_tsvector('english', m.content) @@ plainto_tsquery('english', search_term)
    ORDER BY rank DESC;
END;
$$ LANGUAGE plpgsql;

-- Vector similarity search function
CREATE OR REPLACE FUNCTION vector_search(query_embedding VECTOR(1024), match_threshold FLOAT, match_count INT)
RETURNS TABLE (id UUID, content TEXT, similarity FLOAT) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.content,
        1 - (m.content_embedding <=> query_embedding) AS similarity
    FROM memories m
    WHERE 1 - (m.content_embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Function to update timestamps
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW._updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to refresh the materialized view
CREATE OR REPLACE FUNCTION refresh_memory_graph()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY memory_graph;
    RETURN NULL;
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Error refreshing materialized view: %', SQLERRM;
        RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for updating timestamps
CREATE TRIGGER update_memories_timestamp
BEFORE UPDATE ON memories
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_edge_timestamp
BEFORE UPDATE ON memory_edges
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Function to generate content hash
CREATE OR REPLACE FUNCTION generate_content_hash(content TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN digest(content, 'sha256');
END;
$$ LANGUAGE plpgsql;

-- Function to update content hash
CREATE OR REPLACE FUNCTION update_content_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.content_hash = digest(NEW.content, 'sha256');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_content_hash_trigger
BEFORE INSERT OR UPDATE OF content ON memories
FOR EACH ROW
EXECUTE FUNCTION update_content_hash();

-- Function to log memory changes
CREATE OR REPLACE FUNCTION log_memory_change()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (table_name, record_id, operation, old_values, new_values)
    VALUES (
        TG_TABLE_NAME,
        NEW.id,
        TG_OP,
        row_to_json(OLD),
        row_to_json(NEW)
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER memories_audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON memories
FOR EACH ROW
EXECUTE FUNCTION log_memory_change();

CREATE TRIGGER memory_edges_audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON memory_edges
FOR EACH ROW
EXECUTE FUNCTION log_memory_change();

-- Row Level Security
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_edges ENABLE ROW LEVEL SECURITY;

-- Security policies
CREATE POLICY memory_access_policy ON memories
    USING (true);  -- TODO: Replace with actual policy logic

CREATE POLICY memory_edge_access_policy ON memory_edges
    USING (true);  -- TODO: Replace with actual policy logic

-- Prevent cycles in the graph
CREATE OR REPLACE FUNCTION prevent_cycles()
RETURNS TRIGGER AS $$
DECLARE
    cycle_found BOOLEAN;
BEGIN
    WITH RECURSIVE search_graph(source, target, path, cycle) AS (
        SELECT e.source_id, e.target_id, ARRAY[e.source_id, e.target_id], false
        FROM memory_edges e
        WHERE e.source_id = NEW.source_id
        
        UNION ALL
        
        SELECT sg.source, e.target_id, sg.path || e.target_id, e.target_id = ANY(sg.path)
        FROM memory_edges e, search_graph sg
        WHERE e.source_id = sg.target
        AND NOT sg.cycle
        AND e.source_id != e.target_id  -- Skip self-references
    )
    SELECT EXISTS (
        SELECT 1 FROM search_graph 
        WHERE cycle = true
        LIMIT 1
    ) INTO cycle_found;
    
    IF cycle_found THEN
        RAISE EXCEPTION 'Cycle detected in graph: operation would create a cycle';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add cycle prevention trigger
CREATE TRIGGER prevent_cycle_trigger
BEFORE INSERT OR UPDATE ON memory_edges
FOR EACH ROW
EXECUTE FUNCTION prevent_cycles();

-- Function to generate content hash
CREATE OR REPLACE FUNCTION generate_content_hash(content TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN digest(content, 'sha256');
END;
$$ LANGUAGE plpgsql;

-- Function to update content hash
CREATE OR REPLACE FUNCTION update_content_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.content_hash = digest(NEW.content, 'sha256');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

