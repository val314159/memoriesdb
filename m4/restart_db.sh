#!/bin/bash
(
    set -ex

    export UV_ENV_FILE=$(realpath ./.env)

    set -a

    source .env

    P="${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/${POSTGRES_DB}"

    echo "Resetting database schema..."

    D="DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    docker exec -i pgvector psql "postgresql://$P" -c "$D"

    echo "Setting up database schema..."
    for sql_file in $(ls -1 sql/*_*.sql | sort); do
	echo "Applying $sql_file...";
	docker exec -i pgvector psql "postgres://$P" <$sql_file || exit 1;
    done
    echo "Database schema and initial data setup complete"
    echo "Syncing uv..."
    uv sync
    echo "Syncing complete"
    echo "Loading test chat1.yml..."
    uv run load_convo.py chat1.yml --loadonly | cut -f2 >1.out
    echo "Loading test chat2.yml..."
    uv run load_convo.py chat2.yml --loadonly | cut -f2 >2.out
    echo "Loading complete"

)
