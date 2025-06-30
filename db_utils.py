"""Utility helpers for querying PostgreSQL and getting JSON-friendly dicts.

Features:
• Automatic json-safe conversion of UUID/bytes/memoryview
• Optional flattening of `_metadata` JSONB into top-level keys
"""
from __future__ import annotations

import base64
from typing import Any, Dict, Iterable

from fastapi.encoders import jsonable_encoder

from db_connect import db_cursor

__all__ = ["json_safe", "query_dicts", "iter_query_dicts", "unflatten_row"]

# --- custom encoder ---------------------------------------------------
_CUSTOM_ENCODERS = {
    bytes: lambda b: base64.b64encode(b).decode(),
    memoryview: lambda mv: base64.b64encode(bytes(mv)).decode(),
}
# Optional encoders for vector types
try:
    import numpy as _np  # type: ignore
    _CUSTOM_ENCODERS[_np.ndarray] = lambda arr: arr.tolist()
except ImportError:  # pragma: no cover
    pass
try:
    from pgvector.psycopg2 import Vector as _PGVector  # type: ignore
    _CUSTOM_ENCODERS[_PGVector] = lambda v: list(v)
except ImportError:  # pragma: no cover
    pass

def json_safe(data: Any):
    """Return a JSON-serialisable version of *data* using FastAPI's encoder."""
    return jsonable_encoder(data, custom_encoder=_CUSTOM_ENCODERS)

def row_to_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    """Just JSON-encode the flattened row (cursor already flattened)."""
    return json_safe(row)

def unflatten_row(d: Dict[str, Any], *, meta_fields: set[str] | None = None) -> Dict[str, Any]:
    """Given a *flattened* dict (metadata keys promoted), roll them back under `_metadata`.

    If *meta_fields* is provided, those keys are moved. Otherwise any key not in the
    canonical memory columns list is considered metadata.
    """
    canonical = {
        "id",
        "kind",
        "content",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
        "deleted_at",
        # add other fixed columns here as needed
    }
    meta_fields = meta_fields or (set(d.keys()) - canonical)

    data: Dict[str, Any] = {}
    meta: Dict[str, Any] = {}
    for k, v in d.items():
        (meta if k in meta_fields else data)[k] = v

    if meta:
        data["_metadata"] = meta
    return data

def query_dicts(sql: str, params: Iterable | None = None):
    """Run SQL and return list[dict] already JSON-safe."""
    with db_cursor() as cur:
        cur.execute(sql, params or ())
        return [row_to_dict(row) for row in cur.fetchall()]

def iter_query_dicts(sql: str, params: Iterable | None = None):
    """Yield JSON-safe dicts one-by-one (streaming)."""
    params = params or ()
    with db_cursor() as cur:
        cur.execute(sql, params)
        for row in cur:  # AppCursor flattens
            yield row_to_dict(row)
