import os

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# DB DSN
DSN = os.getenv("DATABASE_URL", "postgresql://YOUR_USER:YOUR_PASS@localhost/YOUR_DB")

# Ollama endpoint if not debug
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
