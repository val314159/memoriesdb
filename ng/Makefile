# MemoriesDB Makefile

# Declare all phony targets
.PHONY: all stop start restart dev clean realclean prune clean-all pgvector-start pgvector-stop pgvector-restart pgvector-wait pgvector-build pgvector-start-custom pgvector-stop-custom pgvector-start-official pgvector-stop-official memories-start memories-stop memories-restart memories-run setup-db db start-workers debug debug-docker logs-dir help

# Variables
PG = pg15
PG_PORT = 54321
PG_CONTAINER_NAME = pgvector
PG_DATA_DIR = ./data/postgres

# Docker run options - use env file for most vars, override port
V = --rm --env-file=.env \
	-v`pwd`/sql:/docker-entrypoint-initdb.d \
	-p${PG_PORT}:5432 \
	--name pgvector pgvector/pgvector:0.8.0-${PG}

# Memory container options - use env file with port override
M = --rm --env-file=.env \
	-e PG_PORT=${PG_PORT} \
	--network=host \
	-e LOG_FILE=/app/logs/memoriesdb.log \
	--name memories memories

# Custom pgvector container options
C = --name $(PG_CONTAINER_NAME) \
	--env-file=.env \
	-v $(PG_DATA_DIR):/var/lib/postgresql/data \
	-p ${PG_PORT}:5432 \
	-d memoriesdb-pgvector

# Log directory
LOG_DIR = ./logs

# Main targets
all: start

stop: pgvector-stop memories-stop

start: pgvector-start memories-start

restart: pgvector-restart memories-restart

# Interactive development mode (preserves data, includes code mounting for debugging)
dev: pgvector-stop pgvector-start-custom pgvector-wait memories-debug

clean:
	find . -name \*~ -o -name .\*~ | xargs rm -fr
	@echo "Cleaned up temporary files"

# PostgreSQL with pgvector
pgvector-start:
	docker run -d ${V}
	@echo "PostgreSQL with pgvector started, waiting for it to be ready..."
	make pgvector-wait
	@echo "PostgreSQL with pgvector is ready on port ${PG_PORT}"

pgvector-stop:
	docker rm -f pgvector || true
	@echo "PostgreSQL container stopped and removed"

pgvector-restart: pgvector-stop pgvector-start

pgvector-wait:
	@echo "Waiting for PostgreSQL to be ready..."
	@until docker logs pgvector 2>&1 | grep -q "database system is ready to accept connections"; do \
		echo -n "."; \
		sleep 1; \
	done
	@echo "\nPostgreSQL is ready!"

# Use custom Dockerfile
# Build custom pgvector image
pgvector-build:
	docker build -t memoriesdb-pgvector -f Dockerfile.pgvector .
	@echo "Custom PostgreSQL image with pgvector built"

# Start custom pgvector container
pgvector-start-custom: pgvector-build
	docker run ${C}
	@echo "Custom PostgreSQL with pgvector started on port $(PG_PORT)"
	@echo "Allow a few seconds for the database to initialize"
	@echo "Then run: make setup-db"

# Stop custom pgvector container
pgvector-stop-custom:
	docker stop $(PG_CONTAINER_NAME)
	docker rm $(PG_CONTAINER_NAME)
	@echo "PostgreSQL container stopped and removed"

# Setup database schema
setup-db: pgvector-wait
	@echo "Setting up database schema..."
	docker exec -i pgvector psql -U $$POSTGRES_USER -d $$POSTGRES_DB < sql/000_setup.sql
	docker exec -i pgvector psql -U $$POSTGRES_USER -d $$POSTGRES_DB < sql/001_memory_mesh.sql
	@echo "Database schema setup complete"

# Reset database schema (drop and recreate)
reset-db: pgvector-wait
	@echo "Resetting database schema..."
	docker exec -i pgvector psql -U memories_user -d memories -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	@echo "Schema dropped, recreating..."
	make setup-db

# Memories container management
M = --rm --env-file=.env --network=host --name memories memories

# Create logs directory if it doesn't exist
logs-dir:
	mkdir -p ${LOG_DIR}
	@echo "Log directory created: ${LOG_DIR}"

memories-start: logs-dir
	docker build . --tag memories ; docker run -d ${M} -v `pwd`/${LOG_DIR}:/app/logs
	@echo "Memories container started"

memories-stop:
	docker rm -f memories || true
	@echo "Memories container stopped"

memories-restart: memories-stop memories-start

memories-run:
	docker build . --tag memories ; docker run -it ${M}
	@echo "Memories container running in interactive mode"

# Database connection
db-connect:
	set -a ; . ./.env ; bash -c "psql postgresql://$$POSTGRES_USER:$$POSTGRES_PASSWORD@localhost:$(PG_PORT)/$$POSTGRES_DB"

# Python virtual environment
.venv:
	uv sync

# Start the workers
start-workers:
	@echo "Starting workers..."
	python embedding_worker.py &
	python vindexing_worker.py &
	@echo "Workers started"

# Local development targets (no Docker)

memories-debug: logs-dir
	@echo "Building and running Docker container in debug mode..."
	docker build -t memories .
	docker run -it --rm ${M} -e DEBUG=true \
		-v `pwd`:/app \
		--name memories-debug memories
	@echo "Debug Docker session ended"

# Refresh target - combines multiple steps for a clean development environment
refresh: memories-stop reset-db memories-debug
	@echo "Environment refreshed with clean database and debug container"

# This is where the second clean target was - removed to fix duplication

# Deep cleaning
realclean: clean
	rm -fr .venv
	find . -name __pycache__ | xargs rm -fr
	tree -I .git -asF . | cat

# Prune docker resources
prune:
	docker compose down -v
	docker volume rm $(docker volume ls -q --filter name=memoriesdb) 2>/dev/null || true
	docker network rm $(docker network ls -q --filter name=memoriesdb) 2>/dev/null || true
	docker system prune -f

# Clean everything
clean-all: pgvector-stop
	rm -rf $(PG_DATA_DIR)
	@echo "Cleaned up database data directory"

# Help
help:
	@echo "MemoriesDB Makefile Commands:"
	@echo "  make pgvector-start-official    - Start PostgreSQL with pgvector using official image"
	@echo "  make pgvector-stop-official     - Stop and remove the official PostgreSQL container"
	@echo "  make pgvector-build             - Build custom PostgreSQL with pgvector image"
	@echo "  make pgvector-start-custom      - Start PostgreSQL with pgvector using custom Dockerfile"
	@echo "  make pgvector-stop-custom       - Stop and remove the custom PostgreSQL container"
	@echo "  make setup-db                   - Set up database schema"
	@echo "  make reset-db                   - Reset database by dropping and recreating schema"
	@echo "  make start-workers             - Start the embedding and indexing workers"
	@echo "  make logs-dir                   - Create logs directory for file logging"
	@echo "  make debug                      - Run services locally in debug mode"
	@echo "  make debug-docker               - Run in Docker container with debug mode and live code mount"
	@echo "  make refresh                    - Complete reset: stop container, reset DB, and start debug Docker"
	@echo "  make clean                      - Stop container and remove data directory"
	@echo "  make help                       - Show this help message"
