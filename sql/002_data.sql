-- Helper function to safely insert or get memory with conflict handling
CREATE OR REPLACE FUNCTION safe_insert_memory(
    p_id UUID,
    p_content TEXT,
    p_metadata JSONB
) RETURNS UUID AS $$
DECLARE
    v_id UUID;
    v_hash BYTEA := digest(p_content, 'sha256');
BEGIN
    -- First try to get by ID
    SELECT id INTO v_id FROM memories WHERE id = p_id;
    
    -- If not found, try to insert
    IF v_id IS NULL THEN
        INSERT INTO memories (id, content, content_hash, _metadata)
        VALUES (p_id, p_content, v_hash, p_metadata)
        ON CONFLICT (content_hash) DO NOTHING
        RETURNING id INTO v_id;
        
        -- If still not inserted (due to content_hash conflict), get the existing ID
        IF v_id IS NULL THEN
            SELECT id INTO v_id 
            FROM memories 
            WHERE content_hash = v_hash 
            ORDER BY _created_at ASC
            LIMIT 1;
        END IF;
    END IF;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    system_id UUID;
    category_id UUID;
    user_id UUID;
    message_id UUID;
    session_id UUID;
    system_role_id UUID;
    user_role_id UUID;
    assistant_role_id UUID;
    initial_session_id UUID;
BEGIN
    -- Begin transaction for atomic operations
    BEGIN

        -- Get or create system categories
        SELECT safe_insert_memory(
            '00000000-0000-4000-8000-000000000100',
            'system_' || gen_random_uuid(),  -- Make content unique
            '{"type": "system_category"}'
        ) INTO system_id;

        -- Insert or get system categories using safe_insert_memory
        SELECT safe_insert_memory(
            '00000000-0000-4000-8000-000000000101',
            'category_' || gen_random_uuid(),
            '{"type": "system_category"}'
        ) INTO category_id;

        SELECT safe_insert_memory(
            '00000000-0000-4000-8000-000000000102',
            'user_' || gen_random_uuid(),
            '{"type": "system_category"}'
        ) INTO user_id;

        SELECT safe_insert_memory(
            '00000000-0000-4000-8000-000000000103',
            'message_' || gen_random_uuid(),
            '{"type": "system_category"}'
        ) INTO message_id;

        SELECT safe_insert_memory(
            '00000000-0000-4000-8000-000000000104',
            'session_' || gen_random_uuid(),
            '{"type": "system_category"}'
        ) INTO session_id;

        -- Insert or get system roles using safe_insert_memory
        SELECT safe_insert_memory(
            '00000000-0000-4000-8000-000000000200',
            'system_role_' || gen_random_uuid(),
            '{"type": "role"}'
        ) INTO system_role_id;

        SELECT safe_insert_memory(
            '00000000-0000-4000-8000-000000000201',
            'user_role_' || gen_random_uuid(),
            '{"type": "role"}'
        ) INTO user_role_id;

        SELECT safe_insert_memory(
            '00000000-0000-4000-8000-000000000202',
            'assistant_role_' || gen_random_uuid(),
            '{"type": "role"}'
        ) INTO assistant_role_id;

        -- Create relationships between system types
        WITH relationships AS (
            SELECT category_id AS src, system_id AS tgt, 'has_type' AS rel
            WHERE category_id IS NOT NULL AND system_id IS NOT NULL
            UNION ALL
            SELECT user_id, system_id, 'has_type'
            WHERE user_id IS NOT NULL AND system_id IS NOT NULL
            UNION ALL
            SELECT message_id, system_id, 'has_type'
            WHERE message_id IS NOT NULL AND system_id IS NOT NULL
            UNION ALL
            SELECT session_id, system_id, 'has_type'
            WHERE session_id IS NOT NULL AND system_id IS NOT NULL
        )
        INSERT INTO memory_edges (source_id, target_id, relation, _metadata)
        SELECT src, tgt, rel, '{}'::jsonb
        FROM relationships
        WHERE NOT EXISTS (
            SELECT 1 FROM memory_edges 
            WHERE source_id = relationships.src 
            AND target_id = relationships.tgt 
            AND relation = relationships.rel
        );

        -- Create initial session if none exists
        IF NOT EXISTS (SELECT 1 FROM memories 
                      WHERE _metadata->>'type' = 'session' 
                      AND _metadata->>'description' = 'Initial system session') THEN
            -- First create the session memory
            INSERT INTO memories (content, _metadata)
            VALUES (
                'Initial Session', 
                jsonb_build_object(
                    'type', 'session',
                    'description', 'Initial system session',
                    'created_at', NOW() AT TIME ZONE 'UTC'
                )
            )
            RETURNING id INTO initial_session_id;

            -- Link it to the session type
            INSERT INTO memory_edges (source_id, target_id, relation, _metadata)
            SELECT 
                initial_session_id, 
                id, 
                'has_type', 
                '{}'::jsonb
            FROM memories 
            WHERE id = '00000000-0000-4000-8000-000000000104'  -- Use the exact ID of the session type
            ON CONFLICT (source_id, target_id, relation) DO NOTHING;
        END IF;

        -- Commit the transaction if we get here
    EXCEPTION WHEN OTHERS THEN
        -- Rollback on any error
        RAISE EXCEPTION 'Error initializing system data: %', SQLERRM;
    END;
END $$;

-- Function to get or create a memory by content
CREATE OR REPLACE FUNCTION get_or_create_memory(
    p_content TEXT,
    p_metadata JSONB DEFAULT '{}'::jsonb
) RETURNS UUID AS $$
DECLARE
    v_id UUID;
    v_hash BYTEA := digest(p_content, 'sha256');
BEGIN
    -- First try to insert, handling conflicts
    INSERT INTO memories (content, content_hash, _metadata)
    VALUES (p_content, v_hash, p_metadata)
    ON CONFLICT (content_hash) DO NOTHING
    RETURNING id INTO v_id;
    
    -- If no row was inserted (due to conflict), get the existing ID
    IF v_id IS NULL THEN
        SELECT id INTO v_id 
        FROM memories 
        WHERE content_hash = v_hash 
        ORDER BY _created_at ASC  -- Get the oldest matching memory
        LIMIT 1;
    END IF;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;
