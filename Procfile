
# the communications hub
hub: sleep 1; python -u hub.py

# load the latest conversation (history + model)
llm: sleep 2; python -u convo.py

#llm: sleep 2; python -u examples/llm.py

jupyter: . .venv/bin/activate && jupyter notebook --allow-root --no-browser
