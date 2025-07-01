import os

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Default connection values for Docker setup
PG_USER = os.getenv("PG_USER", "memories_user")
PG_PASS = os.getenv("PG_PASS", "your_secure_password")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DB = os.getenv("PG_DB", "memories")

# DB DSN - Configured to work with our Docker setup by default
DSN = os.getenv("DATABASE_URL", f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}")

# Ollama endpoint if not debug
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Model configurations
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-minilm")  # Default embedding model
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.1")  # Default chat/tool-calling model
