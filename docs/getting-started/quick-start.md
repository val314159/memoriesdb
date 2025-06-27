# Quick Start Guide

This guide will help you quickly get started with MemoriesDB by walking through the core functionality.

## 1. Create Your First Session

```python
from memoriesdb.api.memory_graph import MemoryGraph
import psycopg2

# Connect to the database
conn = psycopg2.connect("dbname=memories user=memories_user password=your_secure_password")
db = MemoryGraph(conn)

# Create a new session
session = db.create_memory(
    "My First Session",
    metadata={
        "type": "session",
        "description": "Initial test session",
        "tags": ["test", "demo"]
    }
)

print(f"Created session: {session['id']}")
```

## 2. Add Messages to a Session

```python
# Add messages to the session
message1 = db.create_memory(
    "Hello, this is my first message!",
    metadata={
        "type": "message",
        "sender": "user1",
        "session_id": session['id']
    }
)

# Create a reply
message2 = db.create_memory(
    "This is a reply to the first message.",
    metadata={
        "type": "message",
        "sender": "user2",
        "session_id": session['id']
    }
)

# Link the reply to the first message
db.create_edge(
    source_id=message2['id'],
    target_id=message1['id'],
    relation='reply_to',
    metadata={"timestamp": "2025-06-27T10:00:00Z"}
)
```

## 3. Real-time Updates with WebSockets

### Python Client
```python
import websocket
import json

def on_message(ws, message):
    print(f"Received: {message}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("### Connection closed ###")

def on_open(ws):
    print("Connected to WebSocket server")
    # Subscribe to a channel
    ws.send(json.dumps({
        "method": "sub",
        "params": {"channels": ["session_updates"]}
    }))

ws = websocket.WebSocketApp("ws://localhost:5002/ws",
                          on_message=on_message,
                          on_error=on_error,
                          on_close=on_close)
ws.on_open = on_open
ws.run_forever()
```

### JavaScript Client
```javascript
const ws = new WebSocket('ws://localhost:5002/ws?c=session_updates');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
    // Update your UI here
};

// Publish a message
function publishUpdate(sessionId, content) {
    ws.send(JSON.stringify({
        method: 'pub',
        params: {
            channel: 'session_updates',
            content: {
                session_id: sessionId,
                message: content
            }
        }
    }));
}
```

## 4. Search and Query

### Full-text Search
```python
# Search for messages containing "important"
results = db.search_memories("important")
for msg in results:
    print(f"Found: {msg['content']}")
```

### Vector Similarity Search
```python
# Get embedding for a query (using a placeholder function)
query_embedding = get_embedding("search query")

# Find similar content
similar = db.vector_search(query_embedding, limit=5)
for item in similar:
    print(f"Similar: {item['content']} (score: {item['similarity']})")
```

## 5. Fork a Session

```python
# Create a fork of an existing session
fork = db.create_memory(
    "Forked Session",
    metadata={
        "type": "session",
        "forked_from": session['id'],
        "reason": "Exploring alternative approach"
    }
)

# Link the fork to the original session
db.create_edge(
    source_id=fork['id'],
    target_id=session['id'],
    relation='forked_from',
    metadata={"timestamp": "2025-06-27T10:05:00Z"}
)
```

## Next Steps

- Explore the [API Reference](../../api-reference/README.md) for detailed documentation
- Check out the [Examples](../../examples/README.md) for more advanced use cases
- Review [Configuration Options](./configuration.md) for production deployment
