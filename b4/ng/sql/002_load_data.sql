-- Initial Data Load for MemoriesDB
-- ===============================
-- This script loads the system user
-- Run after schema setup: psql -U memories_user -d memories -f 002_load_data.sql

-- ===========================
-- SYSTEM USER
-- ===========================

-- Insert the system user if it doesn't exist
-- This user will be used for system-generated content and operations
INSERT INTO users (id, email, created_at)
VALUES ('00000000-0000-0000-0000-000000000000', 'system@memoriesdb', NOW())
ON CONFLICT (id) DO NOTHING;

-- ===========================
-- NOTIFICATION
-- ===========================

\echo ""
\echo "✅ System user created with ID: 00000000-0000-0000-0000-000000000000"
\echo ""
