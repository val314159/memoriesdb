"""Centralised PostgreSQL connection helper.

Usage:
    from db_connect import DB_PARAMS, get_conn
    with get_conn() as conn, conn.cursor() as cur:
        ...
"""
from __future__ import annotations

import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

class AppCursor(RealDictCursor):
    """Project-specific cursor with handy helpers on top of RealDictCursor."""

    # --- automatic flattening via _dictify override -------------------
    def _dictify(self, row):  # pylint: disable=method-hidden
        """Convert row tuple to dict and flatten `_metadata` column."""
        d = super()._dictify(row)
        meta = d.pop("_metadata", None)
        if isinstance(meta, dict):
            d.update(meta)
        return d

    # --- scalar helper -------------------------------------------------
    def scalar(self):
        """Return the first column of the next row (or None)."""
        row = super().fetchone()
        if row:
            return next(iter(row.values()))
        return None

DB_PARAMS: dict[str, str] = {
    "dbname": os.getenv("DB_NAME", "memories"),
    "user": os.getenv("DB_USER", "memories_user"),
    "password": os.getenv("DB_PASSWORD", "your_secure_password"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
}

def get_conn(*, cursor_factory=AppCursor, **overrides):
    """Return a psycopg2 connection with sensible defaults.

    Extra keyword arguments override values in DB_PARAMS.
    """
    params = {**DB_PARAMS, **overrides, "cursor_factory": cursor_factory}
    return psycopg2.connect(**params)

@contextmanager
def db_cursor(**kwargs):
    """Context manager that yields a cursor and commits on success."""
    with get_conn(**kwargs) as conn:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
