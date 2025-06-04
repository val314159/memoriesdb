FROM ubuntu:22.04
RUN apt-get update
RUN apt-get -y install curl python3-minimal python3-psycopg2
RUN curl -LlSf astral.sh/uv/install.sh|sh
ADD . .
CMD ["/root/.local/bin/uv","run","bottle.py","app"]
