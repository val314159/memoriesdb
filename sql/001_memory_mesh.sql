-- ========================
-- EXTENSIONS
-- ========================
-- Enables UUID generation, hashing, vector similarity, trigram text search
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ========================
-- USERS TABLE
-- ========================
-- Stores all real app users (customers or staff). Use UUIDs for privacy.
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username TEXT UNIQUE NOT NULL,
    display_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================
-- CORE MEMORIES TABLE
-- ========================
-- This is the main memory store.
-- Each memory chunk can hold content + embedding + metadata.
-- Created/updated by your app user UUIDs only.
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v1mc(),
    kind TEXT,
    content TEXT,
    content_hash BYTEA,
    content_embedding VECTOR(1024),
    _metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_content_hash UNIQUE(content_hash),
    CONSTRAINT content_not_empty CHECK (content IS NULL OR content != '')
);

-- ========================
-- MEMORY EDGES TABLE
-- ========================
-- This is the graph connection table.
-- Each edge connects two memories with a relation.
-- Edges track their strength and confidence.
-- Also tied to your app user UUIDs.
CREATE TABLE memory_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v1mc(),
    source_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    relation TEXT NOT NULL CHECK (relation ~ '^[a-z_]+$'),
    strength REAL CHECK (strength >= -1.1 AND strength <= 1.1),
    confidence REAL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    _metadata JSONB DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT no_self_reference CHECK (source_id != target_id),
    CONSTRAINT memory_edges_unique_source_target_relation UNIQUE (source_id, target_id, relation)
);

-- ========================
-- ASYNC SCHEDULE TABLES
-- ========================
-- These track work to do for embedding generation and graph reindexing.
CREATE TABLE embedding_schedule (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v1mc(),
    rec UUID NOT NULL REFERENCES memories(id),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_msg TEXT
);

CREATE TABLE vindexing_schedule (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v1mc(),
    rec UUID NOT NULL REFERENCES memories(id),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_msg TEXT
);

-- ========================
-- AUDIT LOG TABLE
-- ========================
-- Captures ALL changes to memories or edges.
-- Tracks old & new values for full history.
-- Uses your app user UUID.
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    record_id UUID NOT NULL,
    operation TEXT NOT NULL,
    operation_timestamp TIMESTAMPTZ DEFAULT NOW(),
    old_values JSONB,
    new_values JSONB,
    changed_by UUID REFERENCES users(id)
);

-- ========================
-- GRAPH MATERIALIZED VIEW
-- ========================
-- Pre-computes reachability to speed up graph traversals.
-- Refreshed manually or via your async process.
CREATE MATERIALIZED VIEW memory_graph AS
WITH RECURSIVE graph_search AS (
    SELECT
        id,
        ARRAY[id] AS path,
        FALSE AS is_cycle,
        0 AS depth
    FROM memories
    UNION ALL
    SELECT
        m.id,
        gs.path || m.id,
        m.id = ANY(gs.path),
        gs.depth + 1
    FROM memories m
    JOIN memory_edges e ON m.id = e.target_id
    JOIN graph_search gs ON e.source_id = gs.id
    WHERE NOT gs.is_cycle
    AND gs.depth < 100
)
SELECT * FROM graph_search;

-- ========================
-- INDEXES
-- ========================
-- Boosts search performance for full-text, vector & graph traversals.
CREATE INDEX idx_memories_content_gin ON memories USING GIN (to_tsvector('english', content));
CREATE INDEX idx_memories_metadata_gin ON memories USING GIN (_metadata);
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (content_embedding vector_cosine_ops);
CREATE INDEX idx_memory_edges_source ON memory_edges(source_id);
CREATE INDEX idx_memory_edges_target ON memory_edges(target_id);
CREATE INDEX idx_memory_edges_relation ON memory_edges(relation);
CREATE INDEX idx_memory_edges_metadata_gin ON memory_edges USING GIN (_metadata);
CREATE INDEX idx_embedding_schedule_unstarted ON embedding_schedule(started_at) WHERE started_at IS NULL;
CREATE INDEX idx_embedding_schedule_unfinished ON embedding_schedule(finished_at) WHERE finished_at IS NULL;
CREATE INDEX idx_vindexing_schedule_unstarted ON vindexing_schedule(started_at) WHERE started_at IS NULL;
CREATE INDEX idx_vindexing_schedule_unfinished ON vindexing_schedule(finished_at) WHERE finished_at IS NULL;

-- ========================
-- TRIGGERS & FUNCTIONS
-- ========================
-- Automatically hash content.
CREATE OR REPLACE FUNCTION generate_content_hash(content TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN digest(content, 'sha256');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_content_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.content_hash = digest(NEW.content, 'sha256');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_content_hash_trigger
BEFORE INSERT OR UPDATE OF content ON memories
FOR EACH ROW EXECUTE FUNCTION update_content_hash();

-- Audit changes for all memories & edges.
CREATE OR REPLACE FUNCTION log_memory_change()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (table_name, record_id, operation, old_values, new_values, changed_by)
    VALUES (
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        TG_OP,
        row_to_json(OLD),
        row_to_json(NEW),
        current_setting('app.current_user', true)::UUID
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER memories_audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON memories
FOR EACH ROW EXECUTE FUNCTION log_memory_change();

CREATE TRIGGER memory_edges_audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON memory_edges
FOR EACH ROW EXECUTE FUNCTION log_memory_change();

-- Graph materialized view refresher.
CREATE OR REPLACE FUNCTION refresh_memory_graph()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW memory_graph;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER refresh_memory_graph_trigger
AFTER INSERT OR UPDATE OR DELETE ON memories
FOR EACH STATEMENT EXECUTE FUNCTION refresh_memory_graph();

CREATE TRIGGER refresh_memory_edges_graph_trigger
AFTER INSERT OR UPDATE OR DELETE ON memory_edges
FOR EACH STATEMENT EXECUTE FUNCTION refresh_memory_graph();

-- ========================
-- SEARCH FUNCTIONS
-- ========================
-- Raw vector similarity search
CREATE OR REPLACE FUNCTION vector_search(query_embedding VECTOR(1024), match_threshold FLOAT, match_count INT)
RETURNS TABLE (id UUID, content TEXT, similarity FLOAT) AS $$
BEGIN
    RETURN QUERY
    SELECT m.id, m.content, (m.content_embedding <#> query_embedding) AS similarity
    FROM memories m
    WHERE (m.content_embedding <#> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Hybrid: vector + trigram
CREATE OR REPLACE FUNCTION hybrid_search(query_embedding VECTOR(1024), search_term TEXT, cosine_weight FLOAT, trigram_weight FLOAT, limit INT)
RETURNS TABLE (id UUID, content TEXT, score FLOAT) AS $$
BEGIN
    RETURN QUERY
    SELECT m.id, m.content,
        (cosine_weight * (m.content_embedding <#> query_embedding)) +
        (trigram_weight * similarity(m.content, search_term)) AS score
    FROM memories m
    WHERE similarity(m.content, search_term) > 0.1
    ORDER BY score DESC
    LIMIT limit;
END;
$$ LANGUAGE plpgsql;

-- ========================
-- ROW LEVEL SECURITY
-- ========================
-- These policies enforce that only the current user can access their own rows.
-- Uses our UUID-based users table.
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_edges ENABLE ROW LEVEL SECURITY;

CREATE POLICY memory_access_policy ON memories
    USING (created_by = current_setting('app.current_user', true)::UUID);

CREATE POLICY memory_edge_access_policy ON memory_edges
    USING (created_by = current_setting('app.current_user', true)::UUID);

-- ========================
-- HOW TO SET USER
-- ========================
-- From your app, set the current user like this:
-- SET LOCAL app.current_user = '<UUID>';
