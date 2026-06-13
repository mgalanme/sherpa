"""Append-only, hash-chained audit trail.

Each event hashes its own content together with the previous event's hash, producing a
tamper-evident chain. Governance is designed in from day zero, not added retroactively.
When Databricks is not configured (pure local development), events fall back to a local file.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

from .config import get_settings

_LOCAL_LOG = os.path.join("data", "outputs", "audit_local.jsonl")


def _hash(prev_hash: str, body: str) -> str:
    return hashlib.sha256((prev_hash + body).encode("utf-8")).hexdigest()


def record(actor: str, action: str, plan_id: str, payload: dict) -> str:
    s = get_settings()
    event_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat()
    body = json.dumps(
        {
            "event_id": event_id,
            "ts": ts,
            "actor": actor,
            "action": action,
            "plan_id": plan_id,
            "payload": payload,
        },
        sort_keys=True,
        ensure_ascii=False,
    )

    use_databricks = bool(
        s.databricks_host and s.databricks_token and s.databricks_http_path
    )
    if use_databricks:
        from .stores import databricks_store

        prev = databricks_store.last_audit_hash()
        this_hash = _hash(prev, body)
        databricks_store.append_audit_event(
            event_id,
            ts,
            actor,
            action,
            plan_id,
            json.dumps(payload, ensure_ascii=False),
            prev,
            this_hash,
        )
        return this_hash

    # Local fallback
    os.makedirs(os.path.dirname(_LOCAL_LOG), exist_ok=True)
    prev = ""
    if os.path.exists(_LOCAL_LOG):
        with open(_LOCAL_LOG, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
            if lines:
                prev = json.loads(lines[-1]).get("hash", "")
    this_hash = _hash(prev, body)
    with open(_LOCAL_LOG, "a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "event_id": event_id,
                    "ts": ts,
                    "actor": actor,
                    "action": action,
                    "plan_id": plan_id,
                    "payload": payload,
                    "prev_hash": prev,
                    "hash": this_hash,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    return this_hash
