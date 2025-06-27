FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get -y install \
    curl \
    python3-minimal \
    python3-psycopg2 \
    make \
    python3-pip \
    python-is-python3 \
    wget

# Install Python dependencies
RUN pip3 install honcho

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install bottle.py and uv
RUN curl -LlSf bottlepy.org/bottle.py -o /usr/lib/python3/dist-packages/bottle.py
RUN curl -LlSf astral.sh/uv/install.sh | sh

# Create IPython profile and add startup script
RUN mkdir -p /root/.ipython/profile_default/startup
ADD src/memoriesdb/ipython_kernel_config.py /root/.ipython/profile_default/

# Create IPython startup script with common imports
RUN mkdir -p /root/.ipython/profile_default/startup && \
    { \
    echo '# Common imports'; \
    echo 'import numpy as np'; \
    echo 'import pandas as pd'; \
    echo 'import matplotlib.pyplot as plt'; \
    echo '%matplotlib inline'; \
    echo ''; \
    echo '# Project-specific imports'; \
    echo 'import sys'; \
    echo 'sys.path.append("/root/memoriesdb")'; \
    echo 'from memoriesdb.api import *'; \
    } > /root/.ipython/profile_default/startup/00-imports.py

# Add code and set working directory
ADD . /root/memoriesdb
WORKDIR /root/memoriesdb

# Install Python dependencies
RUN /root/.local/bin/uv sync && \
    /root/.local/bin/uv add jupyter uv

# Configure Jupyter
RUN mkdir -p /root/.jupyter/ && \
    echo "c.NotebookApp.ip = '0.0.0.0'" > /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.allow_root = True" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.open_browser = False" >> /root/.jupyter/jupyter_notebook_config.py

# Expose ports
# - 5002: API server
# - 8080: Web interface
# - 8888: Jupyter notebook
EXPOSE 5002 8080 8888

# Start the application
CMD ["bash", "-c", ". .venv/bin/activate && exec honcho start"]
