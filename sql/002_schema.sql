-- ========================
-- EXTENSIONS
-- ========================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ========================
-- CORE TABLE: MEMORIES
-- ========================
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v1mc(),
    kind TEXT,
    content TEXT,
    content_hash BYTEA,
    content_embedding VECTOR(1024),
    _metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    _deleted_at TIMESTAMPTZ,
    created_by UUID,  -- user or group UUID
    updated_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_content_hash UNIQUE(content_hash),
    CONSTRAINT content_not_empty CHECK (content IS NULL OR content != '')
);

-- ========================
-- RELATIONSHIPS
-- ========================
CREATE TABLE memory_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v1mc(),
    source_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    relation TEXT NOT NULL CHECK (relation ~ '^[a-z_]+$'),
    strength REAL CHECK (strength >= -1.1 AND strength <= 1.1),
    confidence REAL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    _metadata JSONB DEFAULT '{}'::jsonb,
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT no_self_reference CHECK (source_id != target_id),
    CONSTRAINT memory_edges_source_target_relation_key UNIQUE (source_id, target_id, relation)
);

-- ========================
-- EMBEDDING SCHEDULE
-- ========================
CREATE TABLE embedding_schedule (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v1mc(),
    rec UUID NOT NULL REFERENCES memories(id),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_msg TEXT
);

-- ========================
-- AUDIT LOG
-- ========================
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    record_id UUID NOT NULL,
    operation TEXT NOT NULL,
    operation_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    old_values JSONB,
    new_values JSONB,
    changed_by UUID
);

-- ========================
-- INDEXES
-- ========================
CREATE INDEX idx_memories_content_gin ON memories USING GIN (to_tsvector('english', content));
CREATE INDEX idx_memories_content_trgm ON memories USING GIN (content gin_trgm_ops);
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (content_embedding vector_cosine_ops);
CREATE INDEX idx_memories_metadata_gin ON memories USING GIN (_metadata);

CREATE INDEX idx_memory_edges_source ON memory_edges(source_id);
CREATE INDEX idx_memory_edges_target ON memory_edges(target_id);
CREATE INDEX idx_memory_edges_relation ON memory_edges(relation);
CREATE INDEX idx_memory_edges_metadata_gin ON memory_edges USING GIN (_metadata);

-- ========================
-- FUNCTION: GENERATE CONTENT HASH
-- ========================
CREATE OR REPLACE FUNCTION generate_content_hash(content TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN digest(content, 'sha256');
END;
$$ LANGUAGE plpgsql;

-- ========================
-- TRIGGER: UPDATE CONTENT HASH
-- ========================
CREATE OR REPLACE FUNCTION update_content_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.content_hash := generate_content_hash(NEW.content);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_content_hash_trigger
BEFORE INSERT OR UPDATE OF content ON memories
FOR EACH ROW
EXECUTE FUNCTION update_content_hash();

-- ========================
-- TRIGGER: INSERT TO EMBEDDING SCHEDULE WHEN CONTENT CHANGES
-- ========================
CREATE OR REPLACE FUNCTION insert_embedding_schedule()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO embedding_schedule (rec) VALUES (NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER add_embedding_schedule_trigger
AFTER INSERT OR UPDATE OF content ON memories
FOR EACH ROW
WHEN (NEW.content IS DISTINCT FROM OLD.content)
EXECUTE FUNCTION insert_embedding_schedule();

-- ========================
-- TRIGGERS: AUDIT
-- ========================
CREATE OR REPLACE FUNCTION log_memory_change()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (table_name, record_id, operation, old_values, new_values)
    VALUES (TG_TABLE_NAME, NEW.id, TG_OP, row_to_json(OLD), row_to_json(NEW));
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

-- ========================
-- MATERIALIZED VIEW: HYBRID SEARCH CACHE (OPTIONAL)
-- ========================
CREATE MATERIALIZED VIEW hybrid_search_cache AS
WITH trigram_matches AS (
  SELECT
    id,
    similarity(content, 'SEARCH_TERM') AS trigram_sim
  FROM memories
  WHERE content % 'SEARCH_TERM'
),
vector_scores AS (
  SELECT
    id,
    1 - (content_embedding <=> '[0.1,0.2,...]') AS vector_sim
  FROM memories
)
SELECT
  t.id,
  (0.7 * v.vector_sim) + (0.3 * t.trigram_sim) AS hybrid_rank
FROM trigram_matches t
JOIN vector_scores v ON t.id = v.id;

-- Refresh the materialized view manually or with a worker:
-- REFRESH MATERIALIZED VIEW hybrid_search_cache;

-- ========================
-- SECURITY (OPTIONAL)
-- ========================
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_edges ENABLE ROW LEVEL SECURITY;

CREATE POLICY memory_access_policy ON memories USING (true);
CREATE POLICY memory_edge_access_policy ON memory_edges USING (true);

-- ========================
-- FULL-TEXT SEARCH
-- ========================
CREATE OR REPLACE FUNCTION search_memories(search_term TEXT)
RETURNS TABLE (id UUID, content TEXT, rank FLOAT) AS $$
BEGIN
    RETURN QUERY
    SELECT id, content,
        ts_rank(to_tsvector('english', content), plainto_tsquery('english', search_term)) AS rank
    FROM memories
    WHERE to_tsvector('english', content) @@ plainto_tsquery('english', search_term)
    ORDER BY rank DESC;
END;
$$ LANGUAGE plpgsql;

-- ========================
-- VECTOR SEARCH
-- ========================
CREATE OR REPLACE FUNCTION vector_search(query_embedding VECTOR(1024), match_threshold FLOAT, match_count INT)
RETURNS TABLE (id UUID, content TEXT, similarity FLOAT) AS $$
BEGIN
    RETURN QUERY
    SELECT id, content,
        1 - (content_embedding <=> query_embedding) AS similarity
    FROM memories
    WHERE 1 - (content_embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
