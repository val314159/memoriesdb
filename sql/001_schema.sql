-- Drop existing objects if they exist
DROP TRIGGER IF EXISTS update_memories_timestamp ON memories;
DROP TRIGGER IF EXISTS refresh_memory_graph_trigger ON memories;
DROP TRIGGER IF EXISTS refresh_memory_edges_graph_trigger ON memory_edges;

DROP FUNCTION IF EXISTS update_modified_column();
DROP FUNCTION IF EXISTS refresh_memory_graph();

DROP MATERIALIZED VIEW IF EXISTS memory_graph;
DROP TABLE IF EXISTS memory_edges CASCADE;
DROP TABLE IF EXISTS memories CASCADE;

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
) PARTITION BY HASH (id);

-- Edge table for all relationships
CREATE TABLE memory_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v1mc(),
    _created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_id UUID NOT NULL,
    target_id UUID NOT NULL,
    relation relation_type NOT NULL,
    weight FLOAT DEFAULT 1.0,
    _metadata JSONB DEFAULT '{}'::jsonb,
    created_by TEXT DEFAULT current_user,
    CONSTRAINT fk_source_memory FOREIGN KEY (source_id) REFERENCES memories(id) ON DELETE CASCADE,
    CONSTRAINT fk_target_memory FOREIGN KEY (target_id) REFERENCES memories(id) ON DELETE CASCADE,
    CONSTRAINT no_self_reference CHECK (source_id != target_id),
    UNIQUE(source_id, target_id, relation)
) PARTITION BY HASH (source_id);

-- Create table partitions for better performance
CREATE TABLE memories_p0 PARTITION OF memories FOR VALUES WITH (modulus 4, remainder 0);
CREATE TABLE memories_p1 PARTITION OF memories FOR VALUES WITH (modulus 4, remainder 1);
CREATE TABLE memories_p2 PARTITION OF memories FOR VALUES WITH (modulus 4, remainder 2);
CREATE TABLE memories_p3 PARTITION OF memories FOR VALUES WITH (modulus 4, remainder 3);

CREATE TABLE memory_edges_p0 PARTITION OF memory_edges FOR VALUES WITH (modulus 4, remainder 0);
CREATE TABLE memory_edges_p1 PARTITION OF memory_edges FOR VALUES WITH (modulus 4, remainder 1);
CREATE TABLE memory_edges_p2 PARTITION OF memory_edges FOR VALUES WITH (modulus 4, remainder 2);
CREATE TABLE memory_edges_p3 PARTITION OF memory_edges FOR VALUES WITH (modulus 4, remainder 3);

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

-- Create materialized view for graph queries
CREATE MATERIALIZED VIEW memory_graph AS
SELECT 
    m.id, m.content,
    jsonb_build_object(
        'incoming', (
            SELECT jsonb_agg(jsonb_build_object(
                'id', e.id,
                'relation', e.relation,
                'source', e.source_id,
                'metadata', e._metadata
            ))
            FROM memory_edges e
            WHERE e.target_id = m.id
        ),
        'outgoing', (
            SELECT jsonb_agg(jsonb_build_object(
                'id', e.id,
                'relation', e.relation,
                'target', e.target_id,
                'metadata', e._metadata
            ))
            FROM memory_edges e
            WHERE e.source_id = m.id
        )
    ) as edges
FROM memories m;

-- Create function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_memory_graph()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW memory_graph;
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

-- Create trigger for content hash updates
CREATE TRIGGER update_content_hash_trigger
BEFORE INSERT OR UPDATE OF content ON memories
FOR EACH ROW
EXECUTE FUNCTION update_content_hash();

-- Create triggers for memories
CREATE TRIGGER update_memories_timestamp
BEFORE UPDATE ON memories
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER memories_audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON memories
FOR EACH ROW
EXECUTE FUNCTION log_memory_change();

-- Create triggers for memory_edges
CREATE TRIGGER update_edge_timestamp
BEFORE UPDATE ON memory_edges
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

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

-- Create trigger to update timestamps
CREATE TRIGGER update_memories_timestamp
BEFORE UPDATE ON memories
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- Create materialized view for graph queries
CREATE MATERIALIZED VIEW memory_graph AS
SELECT 
    m.id, m.content,
    jsonb_build_object(
        'incoming', (
            SELECT jsonb_agg(jsonb_build_object(
                'id', e.id,
                'relation', e.relation,
                'source', e.source_id,
                'metadata', e._metadata
            ))
            FROM memory_edges e
            WHERE e.target_id = m.id
        ),
        'outgoing', (
            SELECT jsonb_agg(jsonb_build_object(
                'id', e.id,
                'relation', e.relation,
                'target', e.target_id,
                'metadata', e._metadata
            ))
            FROM memory_edges e
            WHERE e.source_id = m.id
        )
    ) as edges
FROM memories m;
