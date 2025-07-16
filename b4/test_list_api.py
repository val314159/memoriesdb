#!/usr/bin/env python3
"""
Test /memories/ and /edges/ API endpoints for correct pagination and content.
"""
import os
import httpx
import pytest

API = os.getenv("CHAT_API_URL", "http://localhost:8000")

@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=API) as c:
        yield c

def test_memories_pagination(client):
    r = client.get("/memories/?limit=5&offset=0")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert 0 <= len(data) <= 5
    if data:
        assert "id" in data[0]

def test_edges_pagination(client):
    r = client.get("/edges/?limit=5&offset=0")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert 0 <= len(data) <= 5
    if data:
        assert "source_id" in data[0] and "target_id" in data[0] and "relation" in data[0]
