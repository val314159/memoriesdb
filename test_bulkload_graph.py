#!/usr/bin/env python3
"""
Test for /bulkload_records/ endpoint with UUID-based JSONL graph data.
Checks node/edge counts and samples some node/edge content.
"""
import os, json, random, uuid
import httpx
import pytest

API = os.getenv("CHAT_API_URL", "http://localhost:8000")
TESTDATA = os.path.join(os.path.dirname(__file__), "test_data", "chat_bulkload.jsonl")

@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=API) as c:
        yield c

def test_bulkload_graph(client):
    # Upload the file
    with open(TESTDATA, "rb") as f:
        files = {"file": (os.path.basename(TESTDATA), f, "application/jsonl")}
        r = client.post("/bulkload/", files=files)
        assert r.status_code == 200, r.text
        res = r.json()
        assert res["nodes"] == 25
        assert res["edges"] == 23

    # Check node count in DB via API (if available)
    # (Assumes you have a /memories/ endpoint listing all nodes)
    r2 = client.get("/memories/")
    if r2.status_code == 200:
        nodes = r2.json()
        assert len(nodes) == 25
        sample_node = random.choice(nodes)
        assert "id" in sample_node and uuid.UUID(sample_node["id"])

    # Check edge count in DB via API (if available)
    r3 = client.get("/edges/")
    if r3.status_code == 200:
        edges = r3.json()
        assert len(edges) == 23
        sample_edge = random.choice(edges)
        assert "relation" in sample_edge

    # Optionally sample some node/edge details for spot check
    # (If you have content search endpoints, you can add more checks)
