-- ADVANCED RELATION FEATURES
-- ========================
-- This file contains experimental/advanced features for semantic relation matching.
-- NOT loaded by default - you must explicitly enable these features by calling:
--   SELECT memoriesdb.enable_advanced_relations();

-- Create a schema to keep advanced features contained
CREATE SCHEMA IF NOT EXISTS memoriesdb;

-- Main function to enable all advanced features
CREATE OR REPLACE FUNCTION memoriesdb.enable_advanced_relations() 
RETURNS VOID AS $enable_advanced_relations$
BEGIN
    RAISE NOTICE 'Enabling advanced relation features...';
    
    -- Enable pgvector extension if not already enabled
    CREATE EXTENSION IF NOT EXISTS vector;

    -- Add vector column for semantic relation matching
    EXECUTE 'ALTER TABLE memory_edges 
             ADD COLUMN IF NOT EXISTS relation_embedding VECTOR(384)';

    -- Function to update relation embeddings
    CREATE OR REPLACE FUNCTION memoriesdb.update_relation_embedding()
    RETURNS TRIGGER AS $$
    BEGIN
        -- This is a placeholder - in practice, you'd call an embedding service
        -- NEW.relation_embedding = get_embedding(NEW.relation);
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    -- Trigger to automatically update embeddings
    DROP TRIGGER IF EXISTS update_relation_embedding_trigger ON memory_edges;
    CREATE TRIGGER update_relation_embedding_trigger
    BEFORE INSERT OR UPDATE OF relation ON memory_edges
    FOR EACH ROW
    EXECUTE FUNCTION memoriesdb.update_relation_embedding();

    -- Index for vector similarity search
    CREATE INDEX IF NOT EXISTS idx_memory_edges_relation_embedding 
    ON memory_edges USING ivfflat (relation_embedding vector_l2_ops);

    RAISE NOTICE 'Advanced relation features enabled. Call memoriesdb.find_similar_relations() to use.';
END;
$enable_advanced_relations$ LANGUAGE plpgsql;

-- Function to find similar relations
CREATE OR REPLACE FUNCTION memoriesdb.find_similar_relations(
    query_text TEXT,
    similarity_threshold FLOAT DEFAULT 0.7,
    max_results INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    relation TEXT,
    similarity FLOAT
) AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE EXCEPTION 'pgvector extension not enabled. Call memoriesdb.enable_advanced_relations() first.';
    END IF;
    
    -- In practice, get embedding from a model
    -- query_embedding := get_embedding(query_text);
    
    RETURN QUERY
    SELECT 
        e.id,
        e.relation,
        1 - (e.relation_embedding <=> query_embedding) AS similarity
    FROM memory_edges e
    WHERE e.relation_embedding IS NOT NULL
    -- AND 1 - (e.relation_embedding <=> query_embedding) > similarity_threshold
    ORDER BY similarity DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Example usage (doesn't run automatically):
-- SELECT memoriesdb.enable_advanced_relations();
-- SELECT * FROM memoriesdb.find_similar_relations('replies to');
