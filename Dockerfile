FROM ubuntu:22.04
RUN apt-get update
RUN apt-get -y install curl python3-minimal python3-psycopg2 make python-is-python3
RUN curl -LlSf bottlepy.org/bottle.py -o /usr/lib/python3/dist-packages/bottle.py
RUN curl -LlSf astral.sh/uv/install.sh|sh
ADD   . /root/memoriesdb
WORKDIR /root/memoriesdb
RUN     /root/.local/bin/uv sync
CMD ["bash", "-c", ". .venv/bin/activate;exec honcho start"]
EXPOSE 5002
