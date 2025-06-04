PG=pg15

call:: clean all

all:: pgvector-restart

clean::
	find . -name \*~ -o -name .\*~ | xargs rm -fr
	tree -I .git -a . | cat

serve:: bottle.py
	set -a ; . ./.env ; uv run bottle.py ws

api::
	set -a ; . ./.env ; uv run api.py

bottle.py:
	wget bottlepy.org/bottle.py

db::
	set -a ; . ./.env ; bash -c "psql postgresql://$$POSTGRES_USER:$$POSTGRES_PASSWORD@localhost/$$POSTGRES_DB"


pgvector-restart:: pgvector-stop pgvector-start

pgvector-stop::
	docker rm -f pgvector

pgvector-start::
	docker run --rm -d --env-file=.env -v`pwd`/init.sql:/docker-entrypoint-initdb.d/init.sql -p5432:5432 --name pgvector pgvector/pgvector:0.8.0-${PG}


memories-restart:: memories-stop memories-start

memories-stop::
	docker rm -f memories

memories-start::
	docker build .                                    --tag  memories 
	docker run --rm -d --env-file=.env --network=host --name memories memories
