"""SQLite persistence for Round Table queries.

We use a tiny, dependency-free wrapper around sqlite3 instead of pulling
in SQLAlchemy for this. The schema is small, the access pattern is
simple, and keeping it explicit makes it easy to see exactly what gets
persisted.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

DB_DIR = Path(__file__).resolve().parent
DB_PATH = DB_DIR / "roundtable.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS queries (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_input             TEXT    NOT NULL,
    created_at             TEXT    NOT NULL,
    search_results         TEXT,
    round_table_responses  TEXT,
    moderator_analysis     TEXT,
    final_document_1       TEXT,
    final_document_2       TEXT
);
CREATE INDEX IF NOT EXISTS idx_queries_created_at ON queries(created_at DESC);
"""


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Yield a connection with row access by column name.

    check_same_thread=False lets FastAPI's threadpool share the
    module-level connection safely enough for our simple workload. For
    higher concurrency we'd switch to a per-request connection or a
    pool.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist, and idempotently add new columns.

    Safe to call on every startup. ALTER TABLE inside an `IF NOT EXISTS`
    guard upgrades existing DBs in place without losing data.
    """
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        existing_cols = {
            row["name"] for row in conn.execute("PRAGMA table_info(queries)")
        }
        if "search_results" not in existing_cols:
            conn.execute("ALTER TABLE queries ADD COLUMN search_results TEXT")
        if "round_table_responses" not in existing_cols:
            conn.execute(
                "ALTER TABLE queries ADD COLUMN round_table_responses TEXT"
            )
        if "moderator_analysis" not in existing_cols:
            conn.execute(
                "ALTER TABLE queries ADD COLUMN moderator_analysis TEXT"
            )


def create_query(user_input: str) -> int:
    """Insert a new row for an incoming /query submission and return its id.

    Called *before* any processing so a crash mid-pipeline doesn't lose
    the submission. The search_results and final_document_* columns are
    filled in later by the corresponding update_* helpers.
    """
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO queries (user_input, created_at) VALUES (?, ?)",
            (user_input, created_at),
        )
        return cur.lastrowid


def update_search_results(query_id: int, results: list[dict]) -> None:
    """Persist the Google CSE results as JSON in the search_results column."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE queries SET search_results = ? WHERE id = ?",
            (json.dumps(results), query_id),
        )


def update_round_table_responses(query_id: int, responses: list[dict]) -> None:
    """Persist the Round Table seat responses as JSON."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE queries SET round_table_responses = ? WHERE id = ?",
            (json.dumps(responses), query_id),
        )


def update_moderator_analysis(query_id: int, text: str) -> None:
    """Persist the moderator's summary string."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE queries SET moderator_analysis = ? WHERE id = ?",
            (text, query_id),
        )


def update_results(query_id: int, document_1: str | None, document_2: str | None) -> None:
    """Attach the two final documents once research finishes."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE queries SET final_document_1 = ?, final_document_2 = ? WHERE id = ?",
            (document_1, document_2, query_id),
        )


def list_queries(limit: int = 100) -> list[dict]:
    """Return past queries, most recent first."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, user_input, created_at, search_results,
                   round_table_responses, moderator_analysis,
                   final_document_1, final_document_2
            FROM queries
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
