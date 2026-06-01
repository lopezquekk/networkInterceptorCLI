import sqlite3
import uuid
from datetime import datetime, timezone

from .paths import DB_PATH as _DEFAULT_DB_PATH

# Module-level variable for testability (can be monkeypatched in tests)
DB_PATH = _DEFAULT_DB_PATH


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS captures (
                id                TEXT PRIMARY KEY,
                timestamp         TEXT NOT NULL,
                method            TEXT NOT NULL,
                host              TEXT NOT NULL,
                path              TEXT NOT NULL,
                status_code       INTEGER,
                request_headers   TEXT,
                request_body      TEXT,
                response_headers  TEXT,
                response_body     TEXT,
                is_mocked         INTEGER DEFAULT 0
            )
        """)


def write_capture(method, host, path, status_code,
                  request_headers, request_body,
                  response_headers, response_body,
                  is_mocked=False):
    row_id = str(uuid.uuid4())[:8]
    ts = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO captures VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (row_id, ts, method, host, path, status_code,
             request_headers, request_body,
             response_headers, response_body,
             1 if is_mocked else 0),
        )
    return row_id


def list_captures(url_pattern=None):
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM captures"
        params = []
        if url_pattern:
            query += " WHERE host || path LIKE ?"
            params = [f"%{url_pattern}%"]
        query += " ORDER BY timestamp DESC"
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_capture(capture_id):
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM captures WHERE id = ?", (capture_id,)
        ).fetchone()
    return dict(row) if row else None


def clear_captures():
    with _connect() as conn:
        conn.execute("DELETE FROM captures")
