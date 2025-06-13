#!/usr/bin/env python
import os, psycopg2
from get_embeddings import get_truncated_embeddings


PG_URI = os.getenv('PG_URI',
                   'postgres://postgres:pass@localhost/memories')
DELAY = 2


def connect():
    global cursor
    print("Connecting to DB...")
    conn = psycopg2.connect(PG_URI)
    cursor = conn.cursor()
    return cursor

    
def poll():
    print("Poll for new embeddings...")
    cursor.execute("SELECT id,rec FROM embedding_schedule "
                   "WHERE started_at IS NULL ORDER BY id ASC LIMIT 1")
    return cursor.fetchone()


def process(embed_id, mem_id):
    cursor.execute("SELECT content FROM memories WHERE id==%s", (_mem,))
    (content,) = cursor.fetchone()
    error_msg = None
    cursor.execute("UPDATE embedding_schedule"
                   " SET started_at=NOW()"
                   " WHERE id=%s", (embed_id,))
    try:
        # DO THE PROCESSING
        embeddings = get_truncated_embeddings(content)
        # update results
        cursor.execute("UPDATE memories"
                       " SET content__embeddings=%s::VECTOR"
                       " WHERE id=%s", (embeddings, mem_id,))
    except Exception as e:
        error_msg = str(e)
    finally:
        cursor.execute("UPDATE embedding_schedule"
                       " SET finished_at=NOW(), error_msg=%s"
                       " WHERE id=%s", (error_msg, _id))
        pass
    pass


def delay(delay=DELAY):
    import time
    print(f"No new embeddings, sleep for up to {delay}s...")
    time.sleep(delay)
    pass


connect()
while 1:
    if r:= poll(): process(*r)
    else         : delay()
    pass
