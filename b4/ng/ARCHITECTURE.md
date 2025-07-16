# MemoriesDB: The Memory Merchant's Ledger

A secure memory management system with vector search and graph relationships, built for tracking and trading memories with complete provenance.

## Overview

MemoriesDB is a sophisticated memory management platform that tracks the complete lifecycle of every memory while enabling powerful semantic search and relationship mapping. Built on PostgreSQL's robust security model, it provides a secure environment for memory management with built-in row-level security.

## Key Features

- **Memory Provenance**: Every memory is permanently linked to its creator through PostgreSQL's row-level security
- **Audit Trail**: Complete transaction history with user attribution
- **Ownership Tracking**: Clear chain of custody via database constraints
- **Content Integrity**: SHA-256 hashing for content verification
- **Secure Multi-tenancy**: Row-level security ensures complete isolation between users
- **Vector Search**: Semantic search using pgvector with optimized cosine similarity
- **Graph Relationships**: Track relationships between memories with customizable edge types

## Architecture

## Database Layer: The Memory Ledger

### Schema Overview

1. **Core Tables**:
   - `users`: Memory merchants and their credentials
   - `memories`: Memory assets with content and embeddings
   - `memory_edges`: Provenance and relationships between memories
   - `audit_log`: Immutable record of all memory transactions
   - `embedding_schedule`: Processing queue for new memories
   - `vindexing_schedule`: Queue for search index updates

2. **Provenance Features**:
   - `created_by`/`updated_by` on all tables tracks memory ownership
   - SHA-256 content hashing ensures memory integrity
   - Complete audit trail of all memory transactions
   - Immutable timestamps for creation and updates

3. **Security Model**:
   - Row-level security enforces memory boundaries
   - Each memory is permanently linked to its creator
   - Automatic user context tracking via `app.current_user`
   - No direct table access - all operations through security policies

### Extensions Used

- `uuid-ossp`: UUID generation
- `pgcrypto`: Cryptographic functions
- `vector`: Vector similarity search
- `pg_trgm`: Text pattern matching

### Connection Management

- Uses PgBouncer for efficient connection pooling
- Transaction pooling mode for optimal performance
- Automatic connection recycling
- User context tracking via `application_name`

## Memory Trading Workflow

### Memory Lifecycle

1. **Acquisition**:
   - New memories are ingested with creator attribution
   - Content is hashed for integrity verification
   - Initial metadata is captured in the audit log

2. **Processing**:
   - Memory is queued for embedding generation
   - Vector embeddings are generated and stored
   - Search indexes are updated asynchronously

3. **Trading**:
   - Memory ownership is tracked through `created_by`
   - All transfers are logged in the audit trail
   - Row-level security ensures proper access control

### Security Model

- **User Context**:
  ```sql
  -- Set user context for the current transaction
  SET app.current_user = 'user-uuid';
  ```

- **Row-Level Security**:
  - Users can only access their own memories by default
  - Memory sharing requires explicit grants
  - All access attempts are logged

- **Audit Trail**:
  - Every memory operation is recorded
  - Includes both before and after states
  - Tracks which user performed each action
  - Cannot be modified once created

## Worker Architecture

### Embedding Worker (`embedding_worker.py`)

- **Purpose**: Processes new memories and generates vector embeddings
- **Features**:
  - Processes one memory at a time from the `embedding_schedule`
  - Integrates with Ollama for embeddings
  - Handles errors and retries
  - Updates memory records with generated embeddings
  - Queues view refreshes when complete

### Vector Indexing Worker (`vindexing_worker.py`)

- **Purpose**: Maintains materialized views for fast querying
- **Features**:
  - Processes completed embeddings from `vindexing_schedule`
  - Refreshes the `memory_graph` materialized view
  - Handles errors and retries
  - Maintains search performance at scale

1. **Application Layer**
   - Python backend using async/await
   - Connection pooling via PgBouncer
   - Environment-based configuration

2. **PgBouncer** (Connection Pooling)
   - Manages database connections efficiently
   - Handles connection pooling and multiplexing
   - Configuration in `/etc/pgbouncer/pgbouncer.ini`
   - Transaction pooling mode for optimal performance
   - Automatic connection recycling

3. **PostgreSQL** (Data Storage)
   - Core database with extensions:
     - `uuid-ossp`: For UUID generation
     - `pgcrypto`: For cryptographic functions
     - `vector`: For vector operations and similarity search
     - `pg_trgm`: For text similarity
   - Configuration in `postgresql.conf`
   - Row-level security for multi-tenant isolation

### Core Tables

- `users`: User management and authentication
- `memories`: Core memory storage with vector embeddings
- `memory_edges`: Graph relationships between memories
- `audit_log`: Comprehensive change tracking
- `embedding_schedule`: Queue for embedding processing
- `vindexing_schedule`: Queue for view refresh operations

### Processing Flow

1. **Ingestion**
   - New content is added to `memories` table
   - Triggers automatically add records to `embedding_schedule`
   - Audit log entry created

2. **Embedding Generation**
   - `embedding_worker.py` processes the queue asynchronously
   - Generates vector embeddings using Ollama
   - Updates the memory record with the embedding
   - Adds record to `vindexing_schedule`

3. **Indexing**
   - `vindexing_worker.py` refreshes materialized views
   - Updates graph representation for efficient querying
   - Maintains search performance at scale

### Connection Flow

```
[Application] → [PgBouncer Pool] → [PostgreSQL]
    ↑                                  ↑
    └──────── Worker Processes ────────┘
```

## Components

### Backend Services

1. **Embedding Worker** (`embedding_worker.py`)
   - Asynchronous processing of embedding tasks
   - Integrates with Ollama for vector generation
   - Handles retries and error recovery

2. **Vector Indexing Worker** (`vindexing_worker.py`)
   - Maintains materialized views
   - Optimizes query performance
   - Handles view refresh scheduling

### Configuration

- **Environment Variables** (`.env`):
  - Database connection strings
  - Feature flags
  - Resource limits

- **PgBouncer** (`/etc/pgbouncer/pgbouncer.ini`):
  ```ini
  [databases]
  yourdb = host=localhost port=5432 dbname=yourdb
  
  [pgbouncer]
  listen_port = 6432
  auth_type = md5
  pool_mode = transaction
  max_client_conn = 1000
  default_pool_size = 100
  server_idle_timeout = 10
  ```

## Deployment

### Development
- Single-container setup with Docker Compose
- Automatic schema migration
- Debugging tools enabled

### Production
- Multi-container architecture:
  - PgBouncer for connection pooling
  - PostgreSQL with pgvector
  - Worker processes
- Configuration via environment variables
- Health checks and monitoring

## Performance Considerations

### Connection Pooling
- PgBouncer reduces connection overhead
- Optimal pool size: 2-4 × CPU cores
- Monitor with `SHOW POOLS;`

### Vector Search
- Normalized vectors for consistent performance
- Optimized index types for different query patterns
- Batch processing for bulk operations

## Monitoring

### Key Metrics
- Connection pool utilization
- Query performance
- Queue lengths for workers
- System resources

### Tools
- Built-in PostgreSQL statistics
- PgBouncer admin console
- Custom metrics endpoints

## Scaling

### Vertical
- Increase PostgreSQL resources
- Optimize configuration
- Add read replicas

### Horizontal
- Add more PgBouncer instances
- Shard by user or data type
- Implement caching layer
