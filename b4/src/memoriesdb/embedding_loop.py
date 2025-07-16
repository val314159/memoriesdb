#!/usr/bin/env python
import os
from .get_embeddings import get_truncated_embeddings

from .api import connect as _connect


DELAY = 2


def connect():
    global conn
    global cursor
    print("Connecting to DB...", os.getenv('POSTGRES_HOST'))
    conn = _connect().conn
    cursor = conn.cursor()
    return cursor

    
def poll():
    print("Poll for new embeddings...")
    cursor.execute("SELECT id,rec FROM embedding_schedule "
                   "WHERE started_at IS NULL ORDER BY id ASC LIMIT 1")
    ret = list(cursor.fetchall())
    return ret[0] if ret else None


def process(embed_id, mem_id):
    #cursor = conn.cursor()
    cursor.execute("SELECT content FROM memories WHERE id=%s", (mem_id,))
    (content,) = cursor.fetchone()
    error_msg = None
    print(100)
    #cursor = conn.cursor()
    cursor.execute("UPDATE embedding_schedule"
                   " SET started_at=NOW()"
                   " WHERE id=%s", (embed_id,))
    conn.commit()
    try:
        print(101)
        #cursor = conn.cursor()
        # DO THE PROCESSING
        embeddings = get_truncated_embeddings(content)
        # update results
        print(embeddings)
        print(len(embeddings))
        print(len(embeddings[0]))
        cursor.execute("UPDATE memories"
                       " SET content__embeddings=%s::VECTOR"
                       " WHERE id=%s", (embeddings[0], mem_id,))
        print(102)
    except Exception as e:
        print(103)
        error_msg = str(e)
        print("E:", e)
    finally:
        print(104)
        #cursor = conn.cursor()
        cursor.execute("UPDATE embedding_schedule"
                       " SET finished_at=NOW(), error_msg=%s"
                       " WHERE id=%s", (error_msg, embed_id))
        conn.commit()
        print(105)
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
