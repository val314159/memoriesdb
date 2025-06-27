# MemoriesDB: The Intelligent Conversation Platform

## Overview
MemoriesDB is a revolutionary platform that combines the power of a graph database with real-time pub/sub capabilities, specifically designed for the next generation of AI applications. Built on PostgreSQL's robust foundation, MemoriesDB extends traditional database functionality with specialized features for managing conversational AI data at scale.

### What Makes MemoriesDB Unique?
- **Unified Platform**: Combines graph database, vector search, and real-time pub/sub in one solution
- **AI-Native Design**: Built from the ground up for LLM applications and conversational AI
- **Real-time Updates**: Built-in pub/sub system for instant notifications and event-driven architectures
- **Enterprise-Grade**: Leverages PostgreSQL's reliability while adding specialized AI capabilities
- **Developer Friendly**: Simple, intuitive API that abstracts away database complexity

### Core Technologies
- **Graph Database**: Store and query complex relationships between conversations and data
- **Vector Search**: Native support for semantic search and similarity matching
- **Pub/Sub System**: Real-time event notifications and message broadcasting
- **Audit Trail**: Comprehensive change tracking and history

## Real-time Pub/Sub System

MemoriesDB features a high-performance WebSocket-based pub/sub system implemented in `hub.py`, designed for real-time communication in AI applications.

### Key Features
- **Lightweight Pub/Sub**: Simple yet powerful publish-subscribe pattern
- **WebSocket Support**: Native WebSocket interface for web applications
- **Channel-based**: Organize messages using named channels
- **Efficient**: Built on gevent for high concurrency
- **Simple API**: Easy-to-use methods for pub/sub functionality
- **Ephemeral Messaging**: Messages are only delivered to currently connected clients
- **No Persistence**: Messages are not stored - clients must handle reconnection and state sync

### Core Components
- **Channels**: Named message buses for organizing communication
- **Subscriptions**: Clients can subscribe to multiple channels
- **Message Broadcasting**: Messages are broadcast to all currently connected subscribers
- **Connection-based**: No message persistence - if you're not connected, you won't receive messages
- **Automatic Cleanup**: Automatic cleanup of closed connections and their subscriptions

### Example Usage

#### Server Setup (hub.py)
```python
# Start the WebSocket server
from memoriesdb.hub import app
app.run(host='0.0.0.0', port=5002)
```

#### Client-Side (JavaScript)
```javascript
// Connect to the WebSocket server
const ws = new WebSocket('ws://localhost:5002/ws?c=channel1&c=channel2');

// Handle incoming messages
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

// Publish a message
function publish(channel, content) {
    ws.send(JSON.stringify({
        method: 'pub',
        params: {
            channel: channel,
            content: content
        }
    }));
}

// Example: Send a message
publish('updates', 'Hello, world!');

// Note: If you need to recover missed messages after disconnection,
// you'll need to implement your own synchronization mechanism
// by querying the database when reconnecting.
```

#### Python Client
```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    print(f"Received: {data}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("### Connection closed ###")

def on_open(ws):
    print("Connected to WebSocket server")
    # Subscribe to channels
    ws.send(json.dumps({
        'method': 'pub',
        'params': {
            'channel': 'updates',
            'content': 'Hello from Python!'
        }
    }))

if __name__ == "__main__":
    ws = websocket.WebSocketApp("ws://localhost:5002/ws?c=updates",
                             on_open=on_open,
                             on_message=on_message,
                             on_error=on_error,
                             on_close=on_close)
    ws.run_forever()
```

### Advanced Usage

#### Multiple Channel Subscriptions
```javascript
// Subscribe to multiple channels when connecting
const ws = new WebSocket('ws://localhost:5002/ws?c=updates&c=notifications');

// Or dynamically subscribe later
ws.send(JSON.stringify({
    method: 'sub',
    params: { channels: ['new_channel'] }
}));
```

#### Message Format
```json
{
    "method": "pub",
    "params": {
        "channel": "channel_name",
        "content": "Your message here",
        "metadata": {
            "sender": "user123",
            "timestamp": "2025-06-27T13:20:00Z"
        }
    }
}
```

#### Error Handling and Reconnection
```javascript
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
let reconnectTimeout;

function connectWebSocket() {
    const ws = new WebSocket('ws://localhost:5002/ws?c=updates');
    
    ws.onopen = () => {
        console.log('Connected to WebSocket server');
        reconnectAttempts = 0; // Reset reconnect attempts on successful connection
        
        // Resubscribe to channels if needed
        // ...
    };
    
    ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        
        // Implement exponential backoff for reconnection
        if (reconnectAttempts < maxReconnectAttempts) {
            const timeout = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000); // Cap at 30s
            console.log(`Reconnecting in ${timeout}ms...`);
            
            reconnectTimeout = setTimeout(() => {
                reconnectAttempts++;
                connectWebSocket();
            }, timeout);
        } else {
            console.error('Max reconnection attempts reached');
        }
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        ws.close(); // Ensure the connection is closed on error
    };
    
    return ws;
}

// Initial connection
let ws = connectWebSocket();

// When you need to close the connection
function disconnect() {
    if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
    }
    if (ws) {
        ws.close();
    }
}

// Sync state after reconnection
async function syncAfterReconnect() {
    // Query the database for the latest state
    // This is just an example - implement according to your needs
    const latestState = await fetch('/api/latest-state');
    updateUI(latestState);
}
```

## Core Concepts

### 1. Data Model

#### Memories (Nodes)
- Store all content (messages, sessions, etc.)
- Support rich metadata via JSONB
- Content-addressable via SHA-256 hashing
- Vector embeddings for semantic search

#### Edges
- Define relationships between memories
- Support different relation types (has_type, forked_from, etc.)
- Include weights and metadata

### 2. Key Features

#### Conversation Management
- Threaded conversations with fork support
- Session-based organization
- Message ordering and hierarchy
- Full conversation history tracking

#### Advanced Search
- Full-text search
- Vector similarity search
- Metadata filtering
- Graph traversal queries

#### Security & Audit
- Row-level security
- Comprehensive audit logging
- Content hashing for integrity
- User context tracking

## Schema Details

### Main Tables

#### `memories`
- `id`: UUID primary key
- `content`: Text content
- `content_hash`: SHA-256 hash of content
- `content_embedding`: Vector(1024) for semantic search
- `_metadata`: JSONB for flexible attributes
- `_created_at`/`_updated_at`: Timestamps
- `created_by`/`updated_by`: User context

#### `memory_edges`
- `source_id`/`target_id`: References to memories
- `relation`: Type of relationship
- `weight`: Numeric weight
- `_metadata`: Additional relationship data

#### `audit_log`
- Tracks all changes to memories and edges
- Includes before/after states
- User and timestamp information

## Key Functions

### Session Management
```sql
-- Create a new session
SELECT create_session('Session Title', '{"tags": ["important"]}');

-- Get conversation as formatted text
SELECT get_conversation_text('session-id-here');

-- Get structured conversation data
SELECT * FROM get_formatted_conversation('session-id-here', true);
```

### Search Capabilities
```sql
-- Full-text search
SELECT * FROM search_memories('search term');

-- Vector similarity search
SELECT * FROM vector_search(your_embedding, 0.7, 10);

-- Graph traversal
SELECT * FROM memory_graph 
WHERE id = 'memory-id' 
LIMIT 100;
```

### Message Management
```sql
-- Add message to session
SELECT add_message_to_session(
    'session-id',
    'user',
    'Hello, world!',
    '{"emotion": "happy"}'
);

-- Fork a session
SELECT fork_session('original-session-id', 'New Branch');
```

## Performance Optimizations

1. **Partitioning**
   - Memories and edges are hash-partitioned
   - Improves parallel query performance
   - Better maintenance for large datasets

2. **Indexing**
   - GIN indexes for JSONB and full-text search
   - B-tree for common lookups
   - Specialized indexes for vector search

3. **Materialized Views**
   - Pre-computed graph structures
   - Faster common queries
   - Automatic refresh

## Security Model

### Row-Level Security
- Fine-grained access control
- Policy-based permissions
- Context-aware filtering

### Audit Trail
- Complete change history
- Before/after states
- User attribution

## Best Practices

1. **Session Management**
   - Use `create_session()` for new conversations
   - Fork sessions for branching discussions
   - Tag sessions with metadata for organization

2. **Search Optimization**
   - Use vector search for semantic queries
   - Combine with metadata filters
   - Consider materialized views for common patterns

3. **Performance**
   - Batch operations when possible
   - Use transactions for multiple related operations
   - Monitor query performance with EXPLAIN ANALYZE

## Example Workflow: Real-time Chat Application

Let's build a real-time chat application with MemoriesDB that showcases its unique capabilities:

1. **Initialize a Chat Session**
   ```sql
   -- Create a new chat session
   SELECT create_session(
       'Product Brainstorm', 
       '{"type": "chat", "members": ["alice", "bob"], "status": "active"}'
   );
   
   -- Subscribe to session updates
   LISTEN chat_updates_abc123;  -- Replace abc123 with your session ID
   ```

2. **Exchange Messages**
   ```sql
   -- Alice sends a message
   SELECT add_message_to_session(
       'abc123',
       'alice',
       'I think we should focus on the mobile experience first',
       '{"priority": "high", "sent_at": "2025-06-27T13:20:00Z"}'
   );
   
   -- Bob replies
   SELECT add_message_to_session(
       'abc123',
       'bob',
       'Great point! We can use our new design system components.',
       '{"priority": "normal", "sent_at": "2025-06-27T13:21:30Z"}'
   );
   ```

3. **Real-time Updates in the UI**
   ```javascript
   // WebSocket connection for real-time updates
   const ws = new WebSocket('wss://your-api/ws');
   
   ws.onmessage = (event) => {
     const { channel, payload } = JSON.parse(event.data);
     if (channel === 'chat_updates_abc123') {
       updateChatUI(payload);
     }
   };
   
   // Send a message
   function sendMessage(message) {
     ws.send(JSON.stringify({
       action: 'send_message',
       session_id: 'abc123',
       content: message,
       metadata: { device: 'web', priority: 'normal' }
     }));
   }
   ```

4. **Fork for Specific Topics**
   ```sql
   -- Create a focused discussion about mobile design
   SELECT fork_session(
       'abc123', 
       'Mobile Design Discussion',
       '{"parent_message_id": "msg123", "focus": "mobile_design"}'
   );
   ```

5. **Search and Analyze**
   ```sql
   -- Find all discussions about mobile design
   SELECT * FROM search_memories('mobile design');
   
   -- Get semantic similarity
   SELECT m.content, m._metadata->>'sender' as sender
   FROM memories m
   JOIN (
       SELECT target_id, 1 - (embedding <=> your_embedding_function('mobile design')) as similarity
       FROM memory_embeddings
       WHERE 1 - (embedding <=> your_embedding_function('mobile design')) > 0.7
       ORDER BY similarity DESC
       LIMIT 5
   ) as matches ON m.id = matches.target_id;
   ```

## Maintenance

### Database Setup
1. Run SQL files in order:
   ```
   000_init.sql
   001_schema.sql
   002_data.sql
   003_sessions.sql
   ```

2. Create necessary extensions:
   ```sql
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   CREATE EXTENSION IF NOT EXISTS "vector";
   CREATE EXTENSION IF NOT EXISTS "pgcrypto";
   ```

### Monitoring
- Check `audit_log` for system changes
- Monitor `pg_stat_activity` for active queries
- Review `pg_stat_statements` for query performance

## Troubleshooting

### Common Issues
1. **Permission Denied**
   - Verify RLS policies
   - Check user roles and grants

2. **Performance Problems**
   - Check for missing indexes
   - Review query plans
   - Consider partitioning for large tables

3. **Cycle Detection**
   - The system prevents cycles in the graph
   - Check for circular references in your data

## API Reference

### Core Functions
- `create_session(title, metadata)`: Create new session
- `add_message_to_session(session_id, role, content, metadata)`: Add message
- `fork_session(session_id, new_title)`: Create session fork
- `get_formatted_conversation(session_id, include_metadata)`: Get conversation data
- `search_memories(query)`: Full-text search
- `vector_search(embedding, threshold, limit)`: Semantic search

### Utility Functions
- `update_content_hash()`: Maintain content hashes
- `prevent_cycles()`: Graph integrity
- `log_memory_change()`: Audit logging

## License
[Specify License]

## Contributing
[Contribution Guidelines]

RoleType:
  type: 'category'
  parent: Category
  content: 'role'




User:
  type: 'user'
  parent: U

Role:
  type: 'role'
  parent: R

R:
  content: 'role'

U:
  content: 'user'



  - edge
     - _src
     - _dst

  - edge can be considered





so let's say we have a vertex and an edge

   content  (is the type)
<from>   ---> E ---->   <to>
parent: EdgeType
type: 'edge'

<type>   ---> V ---->  <owner>

