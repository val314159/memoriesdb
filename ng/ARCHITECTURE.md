# MemoriesDB

A vector-based memory system with graph relationships.

## Overview

MemoriesDB is a sophisticated system for storing, embedding, and querying memories with semantic search capabilities. It uses PostgreSQL with vector extensions to provide powerful search features across memory content.

## Architecture

### Database

- **PostgreSQL** with extensions:
  - `uuid-ossp`: For UUID generation
  - `pgcrypto`: For cryptographic functions
  - `vector`: For vector operations and similarity search
  - `pg_trgm`: For text similarity

### Core Tables

- `users`: User management
- `memories`: Core memory storage with vector embeddings
- `memory_edges`: Relationships between memories
- `audit_log`: Change tracking and history
- `embedding_schedule`: Queue for embedding processing
- `vindexing_schedule`: Queue for view refresh operations

### Processing Flow

1. New content is added to `memories` table
2. Triggers automatically add records to `embedding_schedule`
3. `embedding_worker.py` processes the queue and generates embeddings via Ollama
4. Upon completion, records are added to `vindexing_schedule`
5. `vindexing_worker.py` refreshes the materialized view to update the graph representation

## Components

### Backend

- **Workers**:
  - `embedding_worker.py`: Asynchronous service for generating and storing vector embeddings
  - `vindexing_worker.py`: Maintains the graph representation through materialized view refreshes

- **Configuration**:
  - `config.py`: Environment-based configuration settings

### SQL Schema

The SQL implementation includes:

- Vector embeddings for semantic search
- Graph structure with edge relationships
- Triggers for automated workflow
- Materialized view for efficient graph traversal
- Row-level security for multi-user isolation
- Advanced search functions (vector and hybrid)

## Deployment

- Docker support via `Dockerfile`
- Process management with `Procfile`
- Development utilities in `Makefile`
- PostgreSQL with pgvector using official Docker image (`pgvector/pgvector:latest`)
- Custom pgvector Dockerfile available as backup option

## Security Features

- Content hashing for integrity verification
- Row-level security policies for user isolation
- Comprehensive audit logging
- Connection-specific user context via `app.current_user`

## Search Capabilities

- Pure vector search using inner product on normalized vectors (optimized performance)
- Hybrid search combining vector embeddings and trigram text similarity
- Recursive graph traversal for relationship exploration

## Vector Strategy

- All embeddings are normalized to unit length (L2 norm = 1)
- Using inner product operator (`<#>`) for optimized similarity search
- Similarity values range from -1 (opposite) to 1 (identical)
- Default similarity threshold of 0.7 for relevant matches

## Development

- Debug mode for testing without external dependencies
- Error handling and logging in worker processes
