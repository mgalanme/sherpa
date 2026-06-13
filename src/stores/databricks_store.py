"""Databricks SQL access for the curated gold tables and the append-only audit trail.

Lessons applied: explicit column lists on INSERT to avoid Delta schema contamination.
"""

from __future__ import annotations

from contextlib import contextmanager

from ..config import get_settings


@contextmanager
def _connection():
    from databricks import sql

    s = get_settings()
    host = s.databricks_host.replace("https://", "").rstrip("/")
    conn = sql.connect(
        server_hostname=host,
        http_path=s.databricks_http_path,
        access_token=s.databricks_token,
    )
    try:
        yield conn
    finally:
        conn.close()


def _fqtn(table: str) -> str:
    s = get_settings()
    return f"{s.databricks_catalog}.{s.databricks_schema}.{table}"


def append_audit_event(
    event_id: str,
    ts_iso: str,
    actor: str,
    action: str,
    plan_id: str,
    payload: str,
    prev_hash: str,
    this_hash: str,
) -> None:
    """Insert one audit event with an explicit column list (never INSERT without columns)."""
    with _connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO {_fqtn('audit_event')} "
            "(event_id, ts, actor, action, plan_id, payload, prev_hash, hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (event_id, ts_iso, actor, action, plan_id, payload, prev_hash, this_hash),
        )


def last_audit_hash() -> str:
    with _connection() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT hash FROM {_fqtn('audit_event')} ORDER BY ts DESC LIMIT 1")
        row = cur.fetchone()
        return row[0] if row else ""
