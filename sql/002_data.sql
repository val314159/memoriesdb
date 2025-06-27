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
        INSERT INTO memories (id, content, _metadata) 
        VALUES ('00000000-0000-4000-8000-000000000100', 'system', '{"type": "system_category"}')
        ON CONFLICT (id) DO UPDATE SET 
            content = EXCLUDED.content,
            _metadata = EXCLUDED._metadata
        RETURNING id INTO system_id;

        INSERT INTO memories (id, content, _metadata) 
        VALUES 
            ('00000000-0000-4000-8000-000000000101', 'category', '{"type": "system_category"}'),
            ('00000000-0000-4000-8000-000000000102', 'user', '{"type": "system_category"}'),
            ('00000000-0000-4000-8000-000000000103', 'message', '{"type": "system_category"}'),
            ('00000000-0000-4000-8000-000000000104', 'session', '{"type": "system_category"}')
        ON CONFLICT (id) DO UPDATE SET 
            content = EXCLUDED.content,
            _metadata = EXCLUDED._metadata
        RETURNING 
            CASE 
                WHEN content = 'category' THEN id 
            END AS cat_id,
            CASE 
                WHEN content = 'user' THEN id 
            END AS usr_id,
            CASE 
                WHEN content = 'message' THEN id 
            END AS msg_id,
            CASE 
                WHEN content = 'session' THEN id 
            END AS sess_id
        INTO category_id, user_id, message_id, session_id;

        -- Get or create system roles
        INSERT INTO memories (id, content, _metadata) 
        VALUES 
            ('00000000-0000-4000-8000-000000000200', 'system', '{"type": "role"}'),
            ('00000000-0000-4000-8000-000000000201', 'user', '{"type": "role"}'),
            ('00000000-0000-4000-8000-000000000202', 'assistant', '{"type": "role"}')
        ON CONFLICT (id) DO UPDATE SET 
            content = EXCLUDED.content,
            _metadata = EXCLUDED._metadata
        RETURNING 
            CASE 
                WHEN content = 'system' THEN id 
            END AS sys_role_id,
            CASE 
                WHEN content = 'user' THEN id 
            END AS usr_role_id,
            CASE 
                WHEN content = 'assistant' THEN id 
            END AS ast_role_id
        INTO system_role_id, user_role_id, assistant_role_id;

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
        SELECT src, tgt, rel::relation_type, '{}'::jsonb
        FROM relationships
        WHERE NOT EXISTS (
            SELECT 1 FROM memory_edges 
            WHERE source_id = relationships.src 
            AND target_id = relationships.tgt 
            AND relation = relationships.rel::relation_type
        );

        -- Create initial session if none exists
        IF NOT EXISTS (SELECT 1 FROM memories WHERE _metadata->>'type' = 'session') THEN
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
            WHERE content = 'session' AND _metadata->>'type' = 'system_category'
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
    -- Try to find existing memory
    SELECT id INTO v_id 
    FROM memories 
    WHERE content_hash = v_hash 
    LIMIT 1;
    
    -- If not found, create new
    IF v_id IS NULL THEN
        INSERT INTO memories (content, content_hash, _metadata)
        VALUES (p_content, v_hash, p_metadata)
        RETURNING id INTO v_id;
    END IF;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;
