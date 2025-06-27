-- Enable required extensions if not already enabled in 000_init.sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Drop existing tables if they exist (for idempotent migrations)
DROP TRIGGER IF EXISTS update_memories_timestamp ON memories;
DROP TRIGGER IF EXISTS refresh_memory_graph_trigger ON memories;
DROP TRIGGER IF EXISTS refresh_memory_edges_graph_trigger ON memory_edges;

DROP FUNCTION IF EXISTS update_modified_column();
DROP FUNCTION IF EXISTS uuid_generate_v7();
DROP FUNCTION IF EXISTS refresh_memory_graph();

DROP MATERIALIZED VIEW IF EXISTS memory_graph;
DROP TABLE IF EXISTS memory_edges CASCADE;
DROP TABLE IF EXISTS memories CASCADE;

-- Function to generate version 7 UUIDs (time-ordered)
CREATE OR REPLACE FUNCTION uuid_generate_v7()
RETURNS UUID AS $$
BEGIN
    RETURN encode(set_byte(overlay(
        uuid_send(gen_random_uuid())
        PLACING substring(int8send(floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint) FROM 3)
        FROM 1 FOR 6
    ), 6, (b'0111' || (random() * 16)::int::bit(4))::bit(8)::int), 'hex')::uuid;
END;
$$ LANGUAGE plpgsql VOLATILE;

-- Main memories table with time-ordered UUIDs
CREATE TABLE memories (
    -- Time-ordered UUID (version 7)
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),

    -- Temporal tracking
    _created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _deleted_at TIMESTAMPTZ,

    -- Core relationships
    _type VARCHAR(32) NOT NULL,
    _parent UUID REFERENCES memories(id) ON DELETE SET NULL,
    _dst UUID REFERENCES memories(id) ON DELETE SET NULL,
    _src UUID REFERENCES memories(id) ON DELETE SET NULL,
    role_id UUID REFERENCES memories(id) ON DELETE SET NULL,

    -- Content with versioning
    content TEXT,
    content_hash BYTEA,  -- For change detection
    content_embedding VECTOR(1024),

    -- Metadata
    _version INTEGER NOT NULL DEFAULT 1,
    _tags TEXT[],
    _metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Edge table for explicit relationships
CREATE TABLE memory_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    _created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Edge endpoints
    source_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    relationship_type VARCHAR(64) NOT NULL,
    
    -- Edge properties
    weight FLOAT DEFAULT 1.0,
    _metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraint to prevent duplicate edges
    UNIQUE(source_id, target_id, relationship_type)
);

-- Indexes for performance
CREATE INDEX idx_memories_created ON memories(_created_at);
CREATE INDEX idx_memories_parent ON memories(_parent) WHERE _parent IS NOT NULL;
CREATE INDEX idx_memories_type ON memories(_type);
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (content_embedding vector_cosine_ops);
CREATE INDEX idx_memory_edges_source ON memory_edges(source_id);
CREATE INDEX idx_memory_edges_target ON memory_edges(target_id);
CREATE INDEX idx_memory_edges_relationship ON memory_edges(relationship_type);

-- Function to update timestamps
CREATE OR REPLACE FUNCTION update_modified_column() 
RETURNS TRIGGER AS $$
BEGIN
    NEW._updated_at = NOW();
    RETURN NEW; 
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic timestamp updates
CREATE TRIGGER update_memories_timestamp
BEFORE UPDATE ON memories
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- Materialized view for common graph queries
CREATE MATERIALIZED VIEW memory_graph AS
SELECT 
    m.id, m._type, m.content,
    jsonb_build_object(
        'incoming', (
            SELECT jsonb_agg(jsonb_build_object(
                'id', e.id,
                'type', e.relationship_type,
                'source', e.source_id
            ))
            FROM memory_edges e 
            WHERE e.target_id = m.id
        ),
        'outgoing', (
            SELECT jsonb_agg(jsonb_build_object(
                'id', e.id,
                'type', e.relationship_type,
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
COMMENT ON TABLE memories IS 'Core table for storing memory nodes with hierarchical and graph relationships';
COMMENT ON TABLE memory_edges IS 'Explicit relationships between memory nodes';
COMMENT ON MATERIALIZED VIEW memory_graph IS 'Pre-computed graph view of memory relationships';

-- Example usage:
-- SELECT * FROM memory_graph WHERE id = '...';
-- SELECT * FROM memory_edges WHERE source_id = '...' OR target_id = '...';
-- SELECT * FROM memories WHERE content_embedding <-> (SELECT content_embedding FROM memories WHERE id = '...') < 0.8;
