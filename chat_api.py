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
    """Bulk load sessions/messages from a JSON array file. Ignores lines that are blank or start with //."""
    raw = file.file.read().decode()
    # Remove comment lines and blank lines
    filtered = '\n'.join(l for l in raw.splitlines() if l.strip() and not l.strip().startswith('//'))
    data = json.loads(filtered)
    sess_rows, msg_rows = [], []
    now = datetime.utcnow().isoformat()
    for sess in data:
        sid = sess.get('id') or str(uuid.uuid4())
        sess_rows.append((sid, sess.get('title',''), sess['user_id'], sess.get('forked_from'), sess.get('forked_at'), sess.get('created_at') or now, now))
        for m in sess.get('messages', []):
            mid = m.get('id') or str(uuid.uuid4())
            msg_rows.append((mid, sid, m.get('role'), m.get('content'), m.get('timestamp') or now, m.get('name'), json.dumps(m.get('function_call')) if m.get('function_call') else None))
    try:
        with psycopg2.connect(**DB) as conn:
            with conn.cursor() as cur:
                cur.execute("SET app.current_user_id = '00000000-0000-0000-0000-000000000001'")
                execute_values(cur, """
                    INSERT INTO chat_sessions (id, title, user_id, forked_from, forked_at, created_at, updated_at)
                    VALUES %s ON CONFLICT (id) DO NOTHING
                """, sess_rows)
                execute_values(cur, """
                    INSERT INTO chat_messages (id, session_id, role, content, created_at, name, function_call)
                    VALUES %s ON CONFLICT (id) DO NOTHING
                """, msg_rows)
        return {"sessions_loaded": len(sess_rows), "messages_loaded": len(msg_rows)}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/bulkload_records/")
def bulkload_records(file: UploadFile = File(...)):
    """Bulk load sessions/messages from a JSONL file, streaming one line at a time. Each line is a JSON object with a 'kind'."""
    sess_rows, msg_rows = [], []
    now = datetime.utcnow().isoformat()
    for line in file.file:
        try:
            l = line.decode().strip()
            if not l:
                continue
            obj = json.loads(l)
        except Exception:
            continue
        kind = obj.get("kind")
        if kind == "session":
            sid = obj.get('id') or str(uuid.uuid4())
            sess_rows.append((sid, obj.get('title',''), obj['user_id'], obj.get('forked_from'), obj.get('forked_at'), obj.get('created_at') or now, now))
        elif kind == "message":
            mid = obj.get('id') or str(uuid.uuid4())
            msg_rows.append((mid, obj['session_id'], obj.get('role'), obj.get('content'), obj.get('timestamp') or now, obj.get('name'), json.dumps(obj.get('function_call')) if obj.get('function_call') else None))
    try:
        with psycopg2.connect(**DB) as conn:
            with conn.cursor() as cur:
                if sess_rows:
                    execute_values(cur, """
                        INSERT INTO chat_sessions (id, title, user_id, forked_from, forked_at, created_at, updated_at)
                        VALUES %s
                        ON CONFLICT (id) DO NOTHING
                    """, sess_rows)
                if msg_rows:
                    execute_values(cur, """
                        INSERT INTO chat_messages (id, session_id, role, content, timestamp, name, function_call)
                        VALUES %s
                        ON CONFLICT (id) DO NOTHING
                    """, msg_rows)
            conn.commit()
    except Exception as e:
        raise HTTPException(400, f"Bulk load records failed: {e}")
    return {"sessions": len(sess_rows), "messages": len(msg_rows)}

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
