#!/usr/bin/env python3
"""
Test suite for chat_api.py (session/message/fork logic, including forked_at defaulting).
Uses httpx and pytest for API calls and assertions.
"""
import pytest, uuid, os
import httpx
from dotenv import load_dotenv

load_dotenv()
API = os.getenv("CHAT_API_URL", "http://localhost:8000")
USER1 = os.getenv("TEST_USER1", "00000000-0000-0000-0000-000000000001")
USER2 = os.getenv("TEST_USER2", "00000000-0000-0000-0000-000000000002")

TESTDATA = os.path.join(os.path.dirname(__file__), "test_data", "chat_sessions.json")

import json

def test_bulkload_sessions(client):
    # Count sessions/messages in test file
    with open(TESTDATA, "r") as f:
        try:
            data = json.load(f)
        except Exception:
            # Strip comments for JSONC
            lines = [l for l in f if not l.strip().startswith('//')]
            data = json.loads(''.join(lines))
    expected_sessions = len(data)
    expected_messages = sum(len(sess.get('messages', [])) for sess in data)
    # Upload file
    with open(TESTDATA, "rb") as f2:
        files = {"file": ("chat_sessions.json", f2, "application/json")}
        r = client.post("/bulkload/", files=files)
        assert r.status_code == 200 or r.status_code == 201
    # Check sessions
    r2 = client.get("/sessions/")
    assert r2.status_code == 200
    session_ids = [s["id"] for s in r2.json()]
    found = [s for s in session_ids if s.startswith("sess_")]
    assert len(found) >= expected_sessions
    # Check messages for one session
    r3 = client.get(f"/sessions/{data[0]['id']}/messages/")
    assert r3.status_code == 200
    msgs = r3.json()
    assert len(msgs) == len(data[0]['messages'])
    # Check specific content
    assert any("AI alignment" in m["content"] for m in msgs)

@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=API) as c:
        yield c

def test_create_and_fork_session(client):
    # Create base session
    r = client.post("/sessions/", json={
        "title": "Fork Test Base",
        "user_id": USER1,
        "messages": [
            {"role": "user", "content": "Start"},
            {"role": "assistant", "content": "Hello!"}
        ]
    })
    assert r.status_code == 200
    sid = r.json()["id"]

    # Add a message
    r2 = client.post(f"/sessions/{sid}/messages/", json={"role": "user", "content": "Second message"})
    assert r2.status_code == 201
    mid2 = r2.json()["id"]

    # Fork without forked_at (should auto-set to latest message)
    r3 = client.post(f"/sessions/{sid}/fork", params={"user_id": USER2})
    assert r3.status_code == 200
    forked_sid = r3.json()["id"]
    forked_at = r3.json()["forked_at"]
    assert forked_at == mid2

    # Add more messages to original session
    r4 = client.post(f"/sessions/{sid}/messages/", json={"role": "assistant", "content": "After fork"})
    assert r4.status_code == 201
    mid3 = r4.json()["id"]

    # Forked session should NOT see new message
    r5 = client.get(f"/sessions/{forked_sid}/history")
    mids = [m["id"] for m in r5.json()]
    assert mid3 not in mids
    assert forked_at in mids

    # Fork with explicit forked_at (first message)
    r6 = client.get(f"/sessions/{sid}")
    first_mid = r6.json()["messages"][0]["id"]
    r7 = client.post(f"/sessions/{sid}/fork", params={"forked_at": first_mid, "user_id": USER2})
    fork2 = r7.json()["id"]
    r8 = client.get(f"/sessions/{fork2}/history")
    mids2 = [m["id"] for m in r8.json()]
    assert mids2 == [first_mid]

    # Fork from a fork (nested fork)
    r9 = client.post(f"/sessions/{forked_sid}/fork", params={"user_id": USER1})
    fork3 = r9.json()["id"]
    r10 = client.get(f"/sessions/{fork3}/history")
    assert set([m["id"] for m in r10.json()]) == set(mids)

    # New non-forked session
    r11 = client.post("/sessions/", json={"title": "Independent", "user_id": USER1, "messages": [{"role": "user", "content": "Hi"}]})
    assert r11.status_code == 200
    sid2 = r11.json()["id"]
    r12 = client.get(f"/sessions/{sid2}/history")
    assert len(r12.json()) == 1

    # Add message to forked session, ensure it doesn't affect parent
    r13 = client.post(f"/sessions/{forked_sid}/messages/", json={"role": "user", "content": "Forked branch msg"})
    assert r13.status_code == 201
    r14 = client.get(f"/sessions/{sid}/history")
    assert all(m["content"] != "Forked branch msg" for m in r14.json())
