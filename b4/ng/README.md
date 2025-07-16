# MemoriesDB: The Memory Merchant's Ledger

A secure platform for acquiring, managing, and trading memories with built-in provenance tracking and semantic search capabilities.

## Features

- **Memory Provenance**: Track the complete lifecycle of every memory
- **Secure Trading**: Built-in ownership tracking and access control
- **Semantic Search**: Find memories by meaning using vector embeddings
- **Relationship Mapping**: Create and explore connections between memories
- **Audit Trail**: Comprehensive logging of all memory transactions

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Ollama (for production embeddings)

### Development Setup

1. **Start the database**:
   ```bash
   make dev
   ```

2. **Set up the database schema**:
   ```bash
   make setup-db
   ```

3. **Install Python dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Start the workers**:
   ```bash
   python embedding_worker.py &
   python vindexing_worker.py &
   ```

## Memory Management

### Acquiring Memories

```python
from db_utils import create_memory, set_current_user_id

# Set the current merchant's ID
set_current_user_id("merchant-123")

# Acquire a new memory
memory_id = await create_memory("merchant-123", "A rare memory of the first AI winter")
```

### Trading Memories

Memories are traded by transferring ownership through the `created_by` field. All transfers are logged in the audit trail.

### Searching Memories

```python
from db_utils import search_memories_vector

# Search for related memories
related = await search_memories_vector(
    query_embedding=get_embedding("AI history"),
    user_id="merchant-123",
    limit=5
)
```

## Security Model

- Row-level security ensures merchants can only access their own memories
- All operations are logged in the audit trail
- Memory content is hashed for integrity verification
- User context is tracked per-connection

## Configuration

Copy `.env.example` to `.env` and customize:

```ini
# Database
PG_USER=memories_user
PG_PASS=your_secure_password
PG_HOST=localhost
PG_PORT=54321
PG_DB=memories

# Debugging
DEBUG=true
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system architecture and design decisions.

## License

Proprietary - All rights reserved

## EPILOGUE

Always remember, kids: AVOID DECOHERENCE AT ALL COSTS

---

*MemoriesDB - Where memories become assets*
