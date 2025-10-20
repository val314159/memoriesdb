import json
import logging
import os
import signal
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable, List, Optional
import psycopg
from psycopg.rows import dict_row

from config import DSN, DSN2

logger = logging.getLogger("consolidate_daemon")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

NOTIFY_CHANNEL = "embedding_queue"
BATCH_SIZE = 64


@dataclass
class PartialRow:
    id: str
    role: str
    session_id: str
    seq: int
    done: bool
    content: str

def get_dsn() -> str:
    try:
        psycopg.connect(DSN)
        return DSN
    except Exception:
        return DSN2


@contextmanager
def pg_connection():
    conn = psycopg.connect(get_dsn(), autocommit=False, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def listen_loop():
    logger.info("Starting consolidate daemon; listening on %s", NOTIFY_CHANNEL)
    with psycopg.connect(get_dsn(), autocommit=True) as listen_conn:
        listen_conn.execute(f"LISTEN {NOTIFY_CHANNEL};")
        notifications = listen_conn.notifies()
        for notify in notifications:
            memory_id = notify.payload
            try:
                process_notification(memory_id)
            except Exception:
                logger.exception("Error processing notification: %s", memory_id)

def select_next_jobs(conn):                
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH next_jobs AS (
                SELECT rec
                FROM embedding_schedule
                WHERE finished_at IS NULL
                ORDER BY queued_at
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            )
            SELECT rec FROM next_jobs
            """, (BATCH_SIZE,))
        return [row["rec"] for row in cur.fetchall()]

def process_notification(memory_id: str) -> None:
    with pg_connection() as conn:
        with conn.cursor() as cur:
            # Enqueue job for explicit processing
            cur.execute(
                """
                INSERT INTO embedding_schedule(rec)
                VALUES (%s)
                ON CONFLICT DO NOTHING
                """,
                (memory_id,),
            )
        conn.commit()

    draining = True
    while draining:
        with pg_connection() as conn:
            with conn.cursor() as cur:

                jobs = select_next_jobs(conn)
                if not jobs:
                    draining = False
                    break

                processed_sessions: set[str] = set()
                for job_id in jobs:
                    sid = lookup_session_id(conn, job_id)
                    if not sid or sid in processed_sessions:
                        continue
                    partials = fetch_active_partials(conn, sid)
                    consolidate_partials(conn, sid, partials)
                    processed_sessions.add(sid)

                cur.execute(
                    """
                    UPDATE embedding_schedule
                    SET finished_at = NOW()
                    WHERE rec = ANY(%s)
                    """,
                    (jobs,),
                )
            conn.commit()


def lookup_session_id(conn: psycopg.Connection, memory_id: str) -> Optional[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT target_id
            FROM memory_edges
            WHERE relation = 'belongs_to'
              AND source_id = %s
            LIMIT 1
            """,
            (memory_id,),
        )
        row = cur.fetchone()
        return row["target_id"] if row else None


def fetch_active_partials(conn: psycopg.Connection, session_id: str) -> List[PartialRow]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.id,
                   m._metadata->>'role' AS role,
                   e.target_id::uuid    AS session_id,
                   COALESCE((m._metadata->>'seq')::int, 0) AS seq,
                   COALESCE((m._metadata->>'done')::boolean, FALSE) AS done,
                   m.content
            FROM memories m
            JOIN memory_edges e
              ON e.source_id = m.id
             AND e.relation = 'belongs_to'
            WHERE m.kind = 'partial'
              AND e.target_id = %s
              AND m._deleted_at IS NULL
            ORDER BY seq ASC
            """,
            (session_id,),
        )
        rows = [PartialRow(**row) for row in cur.fetchall()]
    return rows


def consolidate_partials(conn: psycopg.Connection, session_id: str, rows: List[PartialRow]) -> None:
    if not rows:
        return

    groups: List[List[PartialRow]] = []
    current: List[PartialRow] = []
    current_role: Optional[str] = None

    for row in rows:
        if current and row.role != current_role:
            groups.append(current)
            current = []
        current.append(row)
        current_role = row.role

        if row.done:
            groups.append(current)
            current = []
            current_role = None

    if current:
        groups.append(current)

    for group in groups:
        if not group:
            continue
        latest = group[-1]
        merged_text = "".join(node.content or "" for node in group)
        promote_group(conn, session_id, latest.id, merged_text, group[:-1])


def promote_group(conn: psycopg.Connection, session_id: str, anchor_id: str, content: str, predecessors: Iterable[PartialRow]) -> None:
    delete_ids = [row.id for row in predecessors]

    with conn.cursor() as cur:
        if delete_ids:
            cur.execute(
                """
                UPDATE memories
                SET _deleted_at = NOW()
                WHERE id = ANY(%s)
                  AND kind = 'partial'
                """,
                (delete_ids,),
            )

        cur.execute(
            """
            UPDATE memories
            SET content     = %s,
                kind        = 'history',
                _deleted_at = NULL
            WHERE id = %s
              AND kind = 'partial'
            """,
            (content, anchor_id),
        )


def handle_shutdown(signum, frame):
    logger.info("Received signal %s, shutting down", signum)
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    listen_loop()


if __name__ == "__main__":
    main()
