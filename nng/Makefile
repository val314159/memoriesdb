
all:: pgvector-restart
	@echo hello

# Pstgres Variables
PG = pg15
PG_PORT = 54321
PG_CONTAINER_NAME = pgvector
PG_DATA_DIR = ./data/postgres

# Docker run options - use env file for most vars, override port
V = --rm --env-file=.env \
	-p${PG_PORT}:5432 \
	--name pgvector pgvector/pgvector:0.8.0-${PG}

# Get list of SQL migration files in order
SQL_FILES = $(wildcard sql/*_*.sql)

P="postgres://$$POSTGRES_USER:$$POSTGRES_PASSWORD@localhost:5432/$$POSTGRES_DB"
D="DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Setup database schema
setup-db: pgvector-wait
	@echo "Setting up database schema..."
	@for sql_file in $(sort $(SQL_FILES)); do \
		echo "Applying $$sql_file..."; \
		docker exec -i ${PG_CONTAINER_NAME} psql $P <$$sql_file || exit 1; \
	done
	@echo "Database schema and initial data setup complete"

# Database connection
db-connect:
	set -a ; . ./.env ; bash -c "psql postgresql://$$POSTGRES_USER:$$POSTGRES_PASSWORD@localhost:$(PG_PORT)/$$POSTGRES_DB"

# Reset database schema (drop and recreate)
reset-db: pgvector-wait
	@echo "Resetting database schema..."
	docker exec -it ${PG_CONTAINER_NAME} bash -c 'psql $P -c $D'
	@echo "Schema dropped, recreating..."
	bash -c "set -a ; . .env ; make setup-db"

# PostgreSQL with pgvector
pgvector-start: _pgvector-start reset-db

_pgvector-start:
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
	sleep 1

