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
from datetime import datetime

load_dotenv()
DB = dict(dbname=os.getenv('DB_NAME','memories'), user=os.getenv('DB_USER','memories_user'), password=os.getenv('DB_PASSWORD','your_secure_password'), host=os.getenv('DB_HOST','localhost'), port=os.getenv('DB_PORT','5432'))

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

@app.post("/bulkload/")
def bulkload(file: UploadFile = File(...)):
    """Bulk load nodes and edges from a JSONL file with edge objects (property-name-as-relation)."""
    reserved = {"kind", "id", "title", "user_id", "created_at", "role", "content", "timestamp", "name", "function_call"}
    node_rows, edge_rows = [], []
    now = datetime.utcnow().isoformat()
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
        # Insert edges for any dict-valued, non-reserved property
        for k, v in obj.items():
            if k in reserved or not isinstance(v, dict):
                continue
            relation = k
            source_id = v.get("source_id", node_id)
            target_id = v.get("target_id", node_id)
            # Remove source_id/target_id/relation from metadata
            meta = {kk:vv for kk,vv in v.items() if kk not in ("source_id","target_id","relation")}
            edge_rows.append((str(uuid.uuid4()), source_id, target_id, relation, meta and json.dumps(meta) or None))
    try:
        with psycopg2.connect(**DB) as conn:
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


@app.get("/sessions/")
def list_sessions():
    with psycopg2.connect(**DB, cursor_factory=RealDictCursor) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM chat_sessions ORDER BY created_at DESC LIMIT 100")
            return cur.fetchall()

@app.get("/sessions/{sid}")
def get_session(sid: str):
    with psycopg2.connect(**DB, cursor_factory=RealDictCursor) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM chat_sessions WHERE id=%s", (sid,))
            sess = cur.fetchone()
            if not sess:
                raise HTTPException(404, "not found")
            cur.execute("SELECT * FROM chat_messages WHERE session_id=%s ORDER BY created_at", (sid,))
            sess['messages'] = cur.fetchall()
            return sess

@app.post("/sessions/")
def create_session(sess: SessIn):
    sid = sess.id or str(uuid.uuid4())
    now = sess.created_at or datetime.utcnow().isoformat()
    try:
        with psycopg2.connect(**DB) as conn:
            with conn.cursor() as cur:
                cur.execute("SET app.current_user_id = %s", (sess.user_id,))
                cur.execute("""
                    INSERT INTO chat_sessions (id, title, user_id, forked_from, forked_at, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (sid, sess.title or '', sess.user_id, sess.forked_from, sess.forked_at, now, now))
                for m in sess.messages:
                    mid = m.id or str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO chat_messages (id, session_id, role, content, created_at, name, function_call)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """, (mid, sid, m.role, m.content, m.timestamp or now, m.name, json.dumps(m.function_call) if m.function_call else None))
        return {"id": sid}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/sessions/{sid}/fork")
def fork_session(sid: str, forked_at: Optional[str] = None, user_id: str = "00000000-0000-0000-0000-000000000001"):
    new_sid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    try:
        with psycopg2.connect(**DB) as conn:
            with conn.cursor() as cur:
                cur.execute("SET app.current_user_id = %s", (user_id,))
                cur.execute("SELECT title FROM chat_sessions WHERE id=%s", (sid,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(404, "not found")
                if not forked_at:
                    # Get latest message id in parent session
                    cur.execute("SELECT id FROM chat_messages WHERE session_id=%s ORDER BY created_at DESC, id DESC LIMIT 1", (sid,))
                    msg_row = cur.fetchone()
                    forked_at = msg_row[0] if msg_row else None
                cur.execute("""
                    INSERT INTO chat_sessions (id, title, user_id, forked_from, forked_at, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (new_sid, row[0] + " (fork)", user_id, sid, forked_at, now, now))
        return {"id": new_sid, "forked_at": forked_at}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get("/sessions/{sid}/history")
def session_history(sid: str):
    """Get all messages in a session, including inherited from forks up to fork point."""
    with psycopg2.connect(**DB, cursor_factory=RealDictCursor) as conn:
        with conn.cursor() as cur:
            history = []
            cur_sid, forked_at = sid, None
            while cur_sid:
                cur.execute("SELECT forked_from, forked_at FROM chat_sessions WHERE id=%s", (cur_sid,))
                row = cur.fetchone()
                cur.execute("SELECT * FROM chat_messages WHERE session_id=%s ORDER BY created_at", (cur_sid,))
                msgs = cur.fetchall()
                if forked_at:
                    msgs = [m for m in msgs if m['id'] and m['id'] <= forked_at]
                history = msgs + history
                if row and row['forked_from']:
                    cur_sid, forked_at = row['forked_from'], row['forked_at']
                else:
                    break
            return history
