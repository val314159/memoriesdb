#!/usr/bin/env python3
"""
Terse but clear FastAPI app for chat sessions/messages with session forking.
- Bulk loader for JSON/JSONL files (Ollama-style)
- Uses psycopg2, FastAPI, and Pydantic
- Assumes DB schema and triggers as in 001_schema.sql
"""
import os, uuid, json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from datetime import datetime, timezone

from db_connect import get_conn as db_connect, db_cursor


app = FastAPI(title="Chat Session API", version="0.1")

class MsgIn(BaseModel):
    id: Optional[str]
    role: str
    content: str
    timestamp: Optional[str]
    name: Optional[str]=None
    function_call: Optional[dict]=None

class SessIn(BaseModel):
    id: Optional[str]
    title: Optional[str]
    user_id: str
    forked_from: Optional[str]=None
    forked_at: Optional[str]=None
    created_at: Optional[str]=None
    messages: List[MsgIn]=[]

# Streamlined variant using AppCursor.safe_iter
@app.get("/memories/")
def list_memories2(limit: int = 100, offset: int = 0):
    """Return memories as JSON-safe dicts via streaming cursor."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM memories ORDER BY id DESC LIMIT %s OFFSET %s",
            (limit, offset),
        )
        return list(cur.safe_iter())

# Streamlined edges endpoint
@app.get("/edges/")
def list_edges2(limit: int = 100, offset: int = 0):
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM memory_edges ORDER BY id DESC LIMIT %s OFFSET %s",
            (limit, offset),
        )
        return list(cur.safe_iter())

@app.post("/bulkload/")
def bulkload(file: UploadFile = File(...)):
    """Bulk load nodes and edges from a JSONL file with edge objects (property-name-as-relation)."""

    reserved = {"kind", "id", "title", "user_id", "created_at", "role", "content", "timestamp", "name", "function_call"}
    node_rows, edge_rows = [], []
    now = datetime.now(timezone.utc).isoformat()
    for line in file.file:
        try:
            l = line.decode().strip()
            if not l:
                continue
            obj = json.loads(l)
        except Exception:
            continue
        node_id = obj.get("id") or str(uuid.uuid4())
        kind = obj.get("kind")
        # Insert node into memories
        content = obj.get("content", obj.get("title", ""))
        node_rows.append((node_id, kind, content, json.dumps({k:v for k,v in obj.items() if k not in reserved})))
        # Insert edges for any dict-valued or array-of-dicts valued, non-reserved property
        for k, v in obj.items():
            if k in reserved:
                continue
                
            # Handle single dictionary case
            if isinstance(v, dict):
                relation = k
                source_id = v.get("source_id", node_id)
                target_id = v.get("target_id", node_id)
                # Remove source_id/target_id/relation from metadata
                meta = {kk:vv for kk,vv in v.items() if kk not in ("source_id","target_id","relation")}
                edge_rows.append((str(uuid.uuid4()), source_id, target_id, relation, meta and json.dumps(meta) or None))
                
            # Handle array of dictionaries case
            elif isinstance(v, list):
                for edge_obj in v:
                    if not isinstance(edge_obj, dict):
                        continue
                    relation = edge_obj.get("relation", k)
                    source_id = edge_obj.get("source_id", node_id)
                    target_id = edge_obj.get("target_id")
                    if not target_id:  # Skip edges without target
                        continue
                    # Remove source_id/target_id/relation from metadata
                    meta = {kk:vv for kk,vv in edge_obj.items() if kk not in ("source_id","target_id","relation")}
                    edge_rows.append((str(uuid.uuid4()), source_id, target_id, relation, meta and json.dumps(meta) or None))
    try:
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SET app.current_user_id = '00000000-0000-0000-0000-000000000001'")
                if node_rows:
                    execute_values(cur, """
                        INSERT INTO memories (id, kind, content, _metadata)
                        VALUES %s
                        ON CONFLICT (id) DO NOTHING
                    """, node_rows)
                if edge_rows:
                    execute_values(cur, """
                        INSERT INTO memory_edges (id, source_id, target_id, relation, _metadata)
                        VALUES %s
                        ON CONFLICT (source_id, target_id, relation) DO NOTHING
                    """, edge_rows)
            conn.commit()
    except Exception as e:
        raise HTTPException(400, f"Bulk load records failed: {e}")
    return {"nodes": len(node_rows), "edges": len(edge_rows)}


# --- Chat sessions stored as graph nodes/edges -----------------------------
# A session is a node in `memories` with kind='chat_session'.
# Edges:
#   session --(in_session)-> message
#   child_session --(forked_from)-> parent_session
# The JSON metadata of each node keeps the original fields.

# --------------------------------------------------------------------------
# Chat sessions/messages represented inside the **graph tables**
# --------------------------------------------------------------------------
#  - Session node   -> memories.kind = 'chat_session'
#  - Message node   -> memories.kind = 'chat_message'
#  - Edge relation  :  session -(has_message)-> message
#  - Fork relation  :  child_session -(forked_from)-> parent_session
# --------------------------------------------------------------------------

@app.get("/sessions/")
def list_sessions(limit: int = 100):
    """Return recent chat sessions sorted by `created_at`."""
    q = """
    SELECT id,
           content                    AS title,
           (_metadata->>'user_id')    AS user_id,
           (_metadata->>'created_at') AS created_at,
           (_metadata->>'forked_from') AS forked_from,
           (_metadata->>'forked_at')   AS forked_at
    FROM memories
    WHERE kind = 'chat_session'
    ORDER BY (_metadata->>'created_at')::timestamptz DESC
    LIMIT %s
    """
    with db_cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q, (limit,))
        return cur.fetchall()


@app.get("/sessions/{sid}")
def get_session(sid: str):
    """Return a session node plus its messages (via `in_session` edges)."""
    with db_cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM memories WHERE id=%s AND kind='chat_session'", (sid,))
        sess = cur.fetchone()
        if not sess:
            raise HTTPException(404, "not found")
        cur.execute(
            """
            SELECT m.*
            FROM memory_edges e
            JOIN memories m ON m.id = e.target_id
            WHERE e.source_id = %s AND e.relation = 'has_message'
            ORDER BY (m._metadata->>'timestamp')::timestamptz, m.id
            """,
            (sid,),
        )
        sess["messages"] = cur.fetchall()
        return sess


@app.post("/sessions/")
def create_session(sess: SessIn):
    sid = sess.id or str(uuid.uuid4())
    now = sess.created_at or datetime.now(timezone.utc).isoformat()

    session_meta = {
        "user_id": sess.user_id,
        "created_at": now,
        "forked_from": sess.forked_from,
        "forked_at": sess.forked_at,
    }

    node_rows = [(sid, "chat_session", sess.title or "", json.dumps(session_meta))]
    edge_rows = []

    # Prepare message nodes and has_message / belongs_to edges
    for m in sess.messages:
        mid = m.id or str(uuid.uuid4())
        m_meta = {
            "role": m.role,
            "timestamp": m.timestamp or now,
            "name": m.name,
            "function_call": m.function_call,
        }
        node_rows.append((mid, "chat_message", m.content, json.dumps(m_meta)))
        edge_rows.append((str(uuid.uuid4()), sid, mid, "has_message", None))
        edge_rows.append((str(uuid.uuid4()), mid, sid, "belongs_to", None))

    try:
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SET app.current_user_id = %s", (sess.user_id,))
                if node_rows:
                    execute_values(
                        cur,
                        """
                        INSERT INTO memories (id, kind, content, _metadata)
                        VALUES %s
                        ON CONFLICT (id) DO NOTHING
                        """,
                        node_rows,
                    )
                if edge_rows:
                    execute_values(
                        cur,
                        """
                        INSERT INTO memory_edges (id, source_id, target_id, relation)
                        VALUES %s
                        ON CONFLICT (source_id, target_id, relation) DO NOTHING
                        """,
                        edge_rows,
                    )
            conn.commit()
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"id": sid}


class ForkReq(BaseModel):
    user_id: str
    forked_at: Optional[str] = None

@app.post("/sessions/{sid}/fork")
def fork_session(sid: str, body: ForkReq):
    """Create a child session node and connect it via `forked_from`.

    Parameters
    ---
    sid : str
        Parent session ID.
    user_id : str
    """
    user_id = body.user_id
    forked_at = body.forked_at

    new_sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    try:
        with db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SET app.current_user_id = %s", (user_id,))
                # fetch parent session title
                cur.execute(
                    "SELECT content FROM memories WHERE id=%s AND kind='chat_session'",
                    (sid,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(404, "parent session not found")

                if not forked_at:
                    # latest message id in parent session
                    cur.execute(
                        """
                        SELECT m.id
                        FROM memory_edges e JOIN memories m ON m.id=e.target_id
                        WHERE e.source_id=%s AND e.relation='has_message'
                        ORDER BY (m._metadata->>'timestamp')::timestamptz DESC, m.id DESC
                        LIMIT 1
                        """,
                        (sid,),
                    )
                    msg_row = cur.fetchone()
                    forked_at = msg_row[0] if msg_row else None

                fork_meta = {
                    "user_id": user_id,
                    "created_at": now,
                    "forked_from": sid,
                    "forked_at": forked_at,
                }

                cur.execute(
                    """
                    INSERT INTO memories (id, kind, content, _metadata)
                    VALUES (%s,'chat_session',%s,%s)
                    """,
                    (new_sid, row[0] + " (fork)", json.dumps(fork_meta)),
                )
                # child -> parent edge
                cur.execute(
                    """
                    INSERT INTO memory_edges (id, source_id, target_id, relation)
                    VALUES (%s,%s,%s,'forked_from')
                    ON CONFLICT (source_id, target_id, relation) DO NOTHING
                    """,
                    (str(uuid.uuid4()), new_sid, sid),
                )
            conn.commit()
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"id": new_sid, "forked_at": forked_at}

@app.get("/sessions/{sid}/history")
def session_history(sid: str):
    """Return messages for a session, recursively including parent sessions up to fork point."""
    with db_cursor(cursor_factory=RealDictCursor) as cur:
        history: List[dict] = []
        cur_sid: Optional[str] = sid
        forked_at: Optional[str] = None
        while cur_sid:
            # get parent link & fork point
            cur.execute(
                "SELECT (_metadata->>'forked_from') AS parent, (_metadata->>'forked_at') AS fork_point FROM memories WHERE id=%s",
                (cur_sid,),
            )
            row = cur.fetchone()
            # fetch messages for current session
            cur.execute(
                """
                SELECT m.*
                FROM memory_edges e JOIN memories m ON m.id=e.target_id
                WHERE e.source_id=%s AND e.relation='has_message'
                ORDER BY (m._metadata->>'timestamp')::timestamptz, m.id
                """,
                (cur_sid,),
            )
            msgs = cur.fetchall()
            if forked_at:
                msgs = [m for m in msgs if m["id"] <= forked_at]
            history = msgs + history
            if row and row["parent"]:
                cur_sid, forked_at = row["parent"], row["fork_point"]
            else:
                break
        return history
