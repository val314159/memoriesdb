-- Session and Conversation Management
-- =================================

-- Function to create a new session with transaction support
CREATE OR REPLACE FUNCTION create_session(
    title TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    OUT session_id UUID
) AS $$
DECLARE
    session_type_id UUID;
    _metadata JSONB;
BEGIN
    -- Validate input
    IF title IS NULL OR title = '' THEN
        RAISE EXCEPTION 'Session title cannot be empty';
    END IF;
    
    -- Prepare metadata
    _metadata := jsonb_build_object(
        'type', 'session',
        'title', title,
        'created_at', NOW() AT TIME ZONE 'UTC',
        'metadata', COALESCE(metadata, '{}'::jsonb)
    );
    
    -- Get the session type ID
    SELECT id INTO session_type_id 
    FROM memories 
    WHERE content = 'session' 
    AND _metadata->>'type' = 'system_category'
    FOR UPDATE;  -- Lock to prevent concurrent modifications
    
    IF session_type_id IS NULL THEN
        RAISE EXCEPTION 'Session type not found in system categories';
    END IF;
    
    -- Use a transaction to ensure atomicity
    BEGIN
        -- Create the session memory
        INSERT INTO memories (content, _metadata)
        VALUES (title, _metadata)
        RETURNING id INTO session_id;
        
        -- Link to session type
        INSERT INTO memory_edges (source_id, target_id, relation, _metadata)
        VALUES (session_id, session_type_id, 'has_type', '{}'::jsonb);
        
        -- Log the creation
        INSERT INTO audit_log (
            table_name, 
            record_id, 
            operation, 
            new_values
        ) VALUES (
            'memories', 
            session_id, 
            'INSERT', 
            jsonb_build_object(
                'content', title,
                '_metadata', _metadata
            )
        );
        
    EXCEPTION WHEN OTHERS THEN
        -- Rollback the transaction on error
        RAISE EXCEPTION 'Failed to create session: %', SQLERRM;
    END;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Enhanced get_session_messages function with better performance
CREATE OR REPLACE FUNCTION get_session_messages(p_session_id UUID)
RETURNS TABLE (
    message_id UUID,
    content TEXT,
    role TEXT,
    fork_depth INTEGER,
    "position" INTEGER,
    session_id UUID,
    fork_chain UUID[]
) AS $$
BEGIN
    -- Input validation
    IF p_session_id IS NULL THEN
        RAISE EXCEPTION 'Session ID cannot be NULL';
    END IF;
    
    -- Check if session exists
    IF NOT EXISTS (SELECT 1 FROM memories WHERE id = p_session_id) THEN
        RAISE EXCEPTION 'Session not found: %', p_session_id;
    END IF;
    
    -- Use a materialized CTE for better performance with large graphs
    RETURN QUERY
    WITH RECURSIVE session_tree AS (
        -- Base case: start with the requested session
        SELECT 
            id, 
            0 as depth,
            ARRAY[id] as fork_chain
        FROM memories 
        WHERE id = p_session_id
        
        UNION ALL
        
        -- Recursive case: find all forked-from sessions
        SELECT 
            e.target_id, 
            st.depth + 1,
            st.fork_chain || e.target_id
        FROM memory_edges e
        JOIN session_tree st ON e.source_id = st.id
        WHERE e.relation = 'forked_from'
        -- Prevent infinite recursion
        AND e.target_id <> ALL(st.fork_chain)
    )
    SELECT 
        m.id,
        m.content,
        COALESCE(m._metadata->>'role', 'system') as role,
        st.depth,
        COALESCE((m._metadata->>'position')::int, 0) as position,
        st.id as session_id,
        st.fork_chain
    FROM memories m
    JOIN memory_edges e ON m.id = e.source_id
    JOIN session_tree st ON e.target_id = st.id
    WHERE e.relation = 'belongs_to'
    ORDER BY st.depth, COALESCE((m._metadata->>'position')::int, 0);
    
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION 'Error retrieving session messages: %', SQLERRM;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Enhanced get_formatted_conversation function with better performance and error handling
CREATE OR REPLACE FUNCTION get_formatted_conversation(
    p_session_id UUID,
    p_include_metadata BOOLEAN DEFAULT FALSE
) 
RETURNS TABLE (
    speaker TEXT,
    message TEXT,
    fork_info TEXT,
    message_id UUID,
    session_id UUID,
    message_metadata JSONB,
    message_timestamptz TIMESTAMPTZ
) AS $$
DECLARE
    v_session_exists BOOLEAN;
    v_messages RECORD;
BEGIN
    -- Input validation
    IF p_session_id IS NULL THEN
        RAISE EXCEPTION 'Session ID cannot be NULL';
    END IF;
    
    -- Check if session exists using a more efficient query
    SELECT EXISTS (
        SELECT 1 
        FROM memories 
        WHERE id = p_session_id
        AND _metadata->>'type' = 'session'
    ) INTO v_session_exists;
    
    IF NOT v_session_exists THEN
        RAISE EXCEPTION 'Session not found or is not a valid session: %', p_session_id;
    END IF;
    
    -- Use a materialized CTE to avoid multiple executions of get_session_messages
    RETURN QUERY
    WITH message_data AS (
        SELECT 
            sm.*,
            m._metadata as message_metadata,
            m._created_at as message_created_at,
            -- Pre-compute fork path for better performance
            (
                SELECT string_agg(m2.content, ' → ' ORDER BY f.idx DESC)
                FROM unnest(sm.fork_chain[1:array_length(sm.fork_chain, 1)-1]) WITH ORDINALITY AS f(sid, idx)
                JOIN LATERAL (
                    SELECT content 
                    FROM memories 
                    WHERE id = f.sid
                    LIMIT 1
                ) m2 ON true
            ) as fork_path
        FROM get_session_messages(p_session_id) sm
        JOIN memories m ON sm.message_id = m.id
    )
    SELECT 
        -- Format speaker with role
        CASE 
            WHEN md.role IS NOT NULL AND md.role != '' 
            THEN md.role || ': '
            ELSE 'unknown: '
        END as speaker,
        
        -- The actual message content
        md.content as message,
        
        -- Fork information if this is from a forked session
        CASE 
            WHEN array_length(md.fork_chain, 1) > 1 
            THEN '(from: ' || COALESCE(md.fork_path, 'unknown session') || ')'
            ELSE '' 
        END as fork_info,
        
        -- Message and session IDs
        md.message_id,
        md.session_id,
        
        -- Optional metadata
        CASE WHEN p_include_metadata THEN md.message_metadata ELSE NULL END as message_metadata,
        
        -- Message timestamp
        md.message_created_at as message_timestamptz
        
    FROM message_data md
    ORDER BY 
        -- First by fork depth (shallowest first)
        md.depth,
        -- Then by position within the session
        md.position,
        -- Finally by creation time as a tiebreaker
        md.message_created_at;
        
EXCEPTION WHEN OTHERS THEN
    -- Log the error with context
    RAISE EXCEPTION 'Error formatting conversation for session %: %', 
        p_session_id, 
        SQLERRM
    USING HINT = 'Check if the session exists and has the correct permissions';
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Add helper function to get conversation as text
CREATE OR REPLACE FUNCTION get_conversation_text(
    p_session_id UUID,
    p_include_metadata BOOLEAN DEFAULT FALSE
) 
RETURNS TEXT AS $$
DECLARE
    v_result TEXT := '';
    v_row RECORD;
BEGIN
    FOR v_row IN 
        SELECT * FROM get_formatted_conversation(p_session_id, p_include_metadata)
    LOOP
        v_result := v_result || 
                   v_row.speaker || 
                   v_row.message || 
                   CASE WHEN v_row.fork_info != '' THEN ' ' || v_row.fork_info ELSE '' END ||
                   E'\n';
    END LOOP;
    
    RETURN v_result;
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION 'Error generating conversation text: %', SQLERRM;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
