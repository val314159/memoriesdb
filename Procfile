# the communications hub
hub: sleep 1; uv run -m memoriesdb.hub

# load the latest conversation (history + model)
llm: sleep 2; uv run -m memoriesdb.convo

# python notebook
jupyter: jupyter notebook --allow-root --no-browser
