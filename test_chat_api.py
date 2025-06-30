#!/usr/bin/env python3
"""
Integration tests for the chat REST API exposed by chat_api.py.
Run the API first (e.g. `make chat_api`).
Tests are idempotent – they use random UUIDs so repeated runs do not
violate primary-key constraints.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime

import httpx
import pytest

# Allow overriding the base URL when running in CI
API = os.getenv("CHAT_API_URL", "http://localhost:8000")

@pytest.fixture(scope="module")
def client():
    """HTTPX client fixture shared across tests."""
    with httpx.Client(base_url=API, timeout=10.0) as c:
        yield c

def _unique_user_id() -> str:
    """Generate a unique user id for every test run."""
    return str(uuid.uuid4())

def _session_payload(user_id: str) -> dict:
    """Return a minimal but valid session creation payload."""
    now = datetime.utcnow().isoformat()
    return {
        "title": "pytest session",
        "user_id": user_id,
        "created_at": now,
        "messages": [
            {
                "role": "user",
                "content": "Hello world from pytest",
                "timestamp": now,
            },
            {
                "role": "assistant",
                "content": "Hi there!",
                "timestamp": now,
            },
        ],
    }

def test_create_and_get_session(client):
    user_id = _unique_user_id()
    payload = _session_payload(user_id)

    # Create session
    r = client.post("/sessions/", json=payload)
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    # Validate UUID round-trip
    assert uuid.UUID(sid)

    # Retrieve the same session
    r2 = client.get(f"/sessions/{sid}")
    assert r2.status_code == 200, r2.text
    sess = r2.json()
    assert sess["id"] == sid
    assert sess["user_id"] == user_id
    assert len(sess["messages"]) == 2


def test_list_sessions_contains_created(client):
    r = client.get("/sessions/")
    assert r.status_code == 200, r.text
    sessions = r.json()
    assert isinstance(sessions, list)
    # There should be at least one session (created by the previous test)
    assert sessions, "No sessions returned from /sessions/"


def test_fork_and_history(client):
    user_id = _unique_user_id()
    parent_payload = _session_payload(user_id)

    # Create parent session
    r_parent = client.post("/sessions/", json=parent_payload)
    assert r_parent.status_code == 200, r_parent.text
    parent_sid = r_parent.json()["id"]

    # Fork the session
    r_fork = client.post(f"/sessions/{parent_sid}/fork", json={"user_id": user_id})
    assert r_fork.status_code == 200, r_fork.text
    fork_sid = r_fork.json()["id"]
    forked_at = r_fork.json().get("forked_at")

    # Child session exists and references parent
    r_child = client.get(f"/sessions/{fork_sid}")
    assert r_child.status_code == 200, r_child.text
    child = r_child.json()
    assert child["forked_from"] == parent_sid

    # History endpoint returns combined chronologically-correct list
    r_hist = client.get(f"/sessions/{fork_sid}/history")
    assert r_hist.status_code == 200, r_hist.text
    history = r_hist.json()
    assert history, "History is empty"

    # Validate constraints: messages belong to either parent or child session.
    for msg in history:
        assert msg["session_id"] in {parent_sid, fork_sid}
        # If message from parent, ensure it is <= fork point when known
        if msg["session_id"] == parent_sid and forked_at:
            assert msg["id"] <= forked_at
