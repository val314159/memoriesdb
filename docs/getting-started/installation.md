# Installation Guide

## Prerequisites

- PostgreSQL 12+
- Python 3.8+
- Node.js 16+ (for frontend development)

## Database Setup

1. **Install PostgreSQL**
   - [Download PostgreSQL](https://www.postgresql.org/download/)
   - Make sure the PostgreSQL service is running

2. **Run the Setup Script**
   ```bash
   # Run as PostgreSQL superuser (usually 'postgres')
   psql -U postgres -f sql/000_setup.sql
   ```
   This will:
   - Create a new database called `memories`
   - Create a user `memories_user` with the password 'your_secure_password'
   - Grant necessary permissions

3. **Initialize the Database**
   ```bash
   # Run as the memories_user
   psql -U memories_user -d memories -f sql/000_init.sql
   psql -U memories_user -d memories -f sql/001_schema.sql
   psql -U memories_user -d memories -f sql/002_data.sql
   psql -U memories_user -d memories -f sql/003_sessions.sql
   ```

## Python Environment Setup

1. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file in the project root:

```ini
# Database connection
DATABASE_URL=postgresql://memories_user:your_secure_password@localhost:5432/memories

# WebSocket server
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=5002

# Optional: Set to 'true' in production
DEBUG=true
```

## Running the Application

1. **Start the WebSocket server**
   ```bash
   python -m memoriesdb.hub
   ```

2. **Start the API server**
   ```bash
   python -m memoriesdb.api.rest
   ```

## Verifying the Installation

1. **Check database tables**
   ```sql
   psql -U memories_user -d memories -c "\dt"
   ```

2. **Test WebSocket connection**
   ```bash
   # In a Python shell
   import websocket
   ws = websocket.create_connection("ws://localhost:5002/ws?c=test")
   ws.send('{"method": "pub", "params": {"channel": "test", "content": "Hello"}}')
   print(ws.recv())
   ```

## Troubleshooting

- **Connection refused**: Make sure PostgreSQL is running and the credentials in `.env` are correct
- **Permission denied**: Verify the database user has the correct permissions
- **Extension not found**: Make sure the PostgreSQL extensions are installed

## Next Steps

- [Quick Start Guide](./quick-start.md)
- [Configuration Reference](./configuration.md)
