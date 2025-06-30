PG=pg15

call:: clean all

all:: start

stop::    pgvector-stop    memories-stop

start::   pgvector-start   memories-start

restart:: pgvector-restart memories-restart

dev:: pgvector-restart pgvector-wait memories-run

sleep5::
	sleep 5

clean::
	find . -name \*~ -o -name .\*~ | xargs rm -fr

realclean:: clean
	rm -fr .venv
	find . -name __pycache__ | xargs rm -fr
	tree -I .git -asF . | cat

oldtest:: api

test:
	set -a ; . ./.env ; .venv/bin/pytest test_bulkload_graph.py
	set -a ; . ./.env ; .venv/bin/pytest test_list_api.py
	set -a ; . ./.env ; .venv/bin/pytest test_json_safe.py
	set -a ; . ./.env ; .venv/bin/pytest test_chat_api.py

.venv:
	uv sync

serve:: .venv bottle.py
	set -a ; . ./.env ; PYTHONPATH=.. uv run bottle.py ws

api::   .venv
	set -a ; . ./.env ; PYTHONPATH=.. uv run api.py

bottle.py:
	wget bottlepy.org/bottle.py

db::
	set -a ; . ./.env ; bash -c "psql postgresql://$$POSTGRES_USER:$$POSTGRES_PASSWORD@localhost/$$POSTGRES_DB"

V=--rm --env-file=.env -v`pwd`/sql:/docker-entrypoint-initdb.d \
	-p5432:5432 --name pgvector pgvector/pgvector:0.8.0-${PG}
M=--rm --env-file=.env --network=host --name memories memories
pgvector-wait::
	@echo "Waiting for PostgreSQL to be ready..."
	@until docker logs pgvector 2>&1 | grep -q "database system is ready to accept connections"; do \
		echo -n "."; \
		sleep 1; \
	done
	@echo "\nPostgreSQL is ready!"
pgvector-restart:: pgvector-stop pgvector-start
memories-restart:: memories-stop memories-start
pgvector-rerun::   pgvector-stop pgvector-run
memories-rerun::   memories-stop memories-run
pgvector-stop::   ; docker rm -f pgvector
memories-stop::   ; docker rm -f memories
pgvector-start::  ;                                 docker run  -d $V
pgvector-run::    ;                                 docker run -it $V
memories-start::  ; docker build . --tag memories ; docker run  -d $M
memories-run::    ; docker build . --tag memories ; docker run -it $M
run-llm::
	. .venv/bin/activate && PYTHONPATH=. honcho start -f examples/llm.Procfile
chat::
	uv run -m memoriesdb.chat
hub::
	uv run -m memoriesdb.hub

prune::
	docker compose down -v
	docker  volume rm $(docker  volume ls -q --filter name=memoriesdb) 2>/dev/null || true
	docker network rm $(docker network ls -q --filter name=memoriesdb) 2>/dev/null || true
	docker system prune -f

up:: dn
	COMPOSE_BAKE=true docker compose up --build

dn::
down::
	docker compose down -v

chat_api::
	uvicorn chat_api:app --reload
