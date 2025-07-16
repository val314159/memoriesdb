#!/bin/bash
# Script to enable PostgreSQL extensions when database initializes

set -e

# Function to enable extensions
enable_extensions() {
  local db=$1
  echo "Enabling extensions for database: $db"
  
  # Connect to the database and create extensions
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";
    CREATE EXTENSION IF NOT EXISTS "vector";
    
    -- Verify the extensions were created
    SELECT 'Extensions enabled:' as message;
    SELECT extname, extversion FROM pg_extension WHERE extname IN ('uuid-ossp', 'pgcrypto', 'pg_trgm', 'vector');
EOSQL
}

# Wait for PostgreSQL to be ready
until pg_isready; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

# Enable extensions for the default database
enable_extensions "$POSTGRES_DB"

echo "✅ All extensions enabled successfully"
