# the communications hub
hub: sleep 1; uv run -m memoriesdb.hub

# load the latest conversation (history + model)
#llm: sleep 2; uv run -m memoriesdb.convo

# loop and look for embeddings we need to make
emb: sleep 3; uv run -m memoriesdb.embedding_loop

# python notebook
jupyter: jupyter notebook --allow-root --no-browser
