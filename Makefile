PG=pg15

call:: clean all

all:: start

stop::    pgvector-stop    memories-stop

start::   pgvector-start   memories-start

restart:: pgvector-restart memories-restart

sleep5::
	sleep 5

clean::
	find . -name \*~ -o -name .\*~ | xargs rm -fr

realclean:: clean
	rm -fr .venv
	find . -name __pycache__ | xargs rm -fr
	tree -I .git -asF . | cat

test:: api

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
pgvector-restart:: pgvector-stop pgvector-start
memories-restart:: memories-stop memories-start
pgvector-stop::
	docker rm -f pgvector
pgvector-start::
	docker run  -d $V
pgvector-run::
	docker run -it $V
memories-stop::
	docker rm -f memories
memories-start::
	docker build   .   --tag memories
	docker run   -d $M
memories-run::
	docker build   .   --tag memories
	docker run -it $M

run-llm::
	. .venv/bin/activate && PYTHONPATH=. honcho start -f examples/llm.Procfile

chat::
	uv run -m memoriesdb.chat

hub::
	uv run -m memoriesdb.hub
