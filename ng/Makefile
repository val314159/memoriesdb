# MemoriesDB Makefile

# Declare all phony targets
.PHONY: all stop start restart dev clean realclean prune clean-all pgvector-start pgvector-stop pgvector-restart pgvector-wait pgvector-build pgvector-start-custom pgvector-stop-custom pgvector-start-official pgvector-stop-official memories-start memories-stop memories-restart memories-run setup-db db start-workers debug debug-docker help

# Variables
PG = pg15
V = --rm --env-file=.env -v`pwd`/sql:/docker-entrypoint-initdb.d \
	-p5432:5432 --name pgvector pgvector/pgvector:0.8.0-${PG}
M = --rm --env-file=.env --network=host --name memories memories

# Main targets
all: start

stop: pgvector-stop memories-stop

start: pgvector-start memories-start

restart: pgvector-restart memories-restart

dev: pgvector-restart pgvector-wait memories-run

clean:
	find . -name \*~ -o -name .\*~ | xargs rm -fr
	@echo "Cleaned up temporary files"

# PostgreSQL with pgvector
pgvector-start:
	docker run -d ${V}
	@echo "PostgreSQL with pgvector started, waiting for it to be ready..."
	make pgvector-wait
	@echo "PostgreSQL with pgvector is ready on port 5432"

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
	docker run --name $(PG_CONTAINER_NAME) \
		-e POSTGRES_USER=$(PG_USER) \
		-e POSTGRES_PASSWORD=$(PG_PASSWORD) \
		-e POSTGRES_DB=$(PG_DB) \
		-v $(PG_DATA_DIR):/var/lib/postgresql/data \
		-p $(PG_PORT):5432 \
		-d memoriesdb-pgvector
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

# Memories container management
M = --rm --env-file=.env --network=host --name memories memories

memories-start: 
	docker build . --tag memories ; docker run -d ${M}
	@echo "Memories container started"

memories-stop:
	docker rm -f memories || true
	@echo "Memories container stopped"

memories-restart: memories-stop memories-start

memories-run:
	docker build . --tag memories ; docker run -it ${M}
	@echo "Memories container running in interactive mode"

# Database connection
db:
	set -a ; . ./.env ; bash -c "psql postgresql://$$POSTGRES_USER:$$POSTGRES_PASSWORD@localhost/$$POSTGRES_DB"

# Python virtual environment
.venv:
	uv sync

# Start the workers
start-workers:
	@echo "Starting workers..."
	python embedding_worker.py &
	python vindexing_worker.py &
	@echo "Workers started"

# Debug targets
debug: setup-db
	@echo "Starting services in debug mode..."
	@export DEBUG=true && \
	honcho start
	@echo "Debug session ended"

debug-docker: 
	@echo "Building and running Docker container in debug mode..."
	docker build -t memories .
	docker run -it --rm --env-file=.env -e DEBUG=true --network=host \
		-v `pwd`:/app \
		--name memories-debug memories
	@echo "Debug Docker session ended"

# Clean operations
clean:
	find . -name \*~ -o -name .\*~ | xargs rm -fr
	@echo "Cleaned up temporary files"

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
# Help
help:
	@echo "MemoriesDB Makefile Commands:"
	@echo "  make pgvector-start-official    - Start PostgreSQL with pgvector using official image"
	@echo "  make pgvector-stop-official     - Stop and remove the official PostgreSQL container"
	@echo "  make pgvector-build             - Build custom PostgreSQL with pgvector image"
	@echo "  make pgvector-start-custom      - Start PostgreSQL with pgvector using custom Dockerfile"
	@echo "  make pgvector-stop-custom       - Stop and remove the custom PostgreSQL container"
	@echo "  make setup-db                   - Set up database schema"
	@echo "  make start-workers             - Start the embedding and indexing workers"
	@echo "  make debug                      - Run services locally in debug mode"
	@echo "  make debug-docker               - Run in Docker container with debug mode and live code mount"
	@echo "  make clean                      - Stop container and remove data directory"
	@echo "  make help                       - Show this help message"
