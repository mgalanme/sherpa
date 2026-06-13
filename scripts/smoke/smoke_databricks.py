#!/usr/bin/env python3
"""smoke_databricks.py - Verifies the Databricks SQL Warehouse connection used by the app
for gold tables and the audit trail. Reads DATABRICKS_HOST, DATABRICKS_HTTP_PATH and
DATABRICKS_TOKEN from the environment. Run inside .venv-langchain.
"""

import os
import sys

from databricks import sql

host = os.environ.get("DATABRICKS_HOST", "").replace("https://", "").rstrip("/")
http_path = os.environ.get("DATABRICKS_HTTP_PATH", "")
token = os.environ.get("DATABRICKS_TOKEN", "")

if not (host and http_path and token):
    print(
        "  [FAIL] DATABRICKS_HOST, DATABRICKS_HTTP_PATH and DATABRICKS_TOKEN must all be set."
    )
    sys.exit(1)

try:
    with sql.connect(
        server_hostname=host, http_path=http_path, access_token=token
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok")
            assert cur.fetchone()[0] == 1
    print(f"  [ OK ] Databricks SQL Warehouse reachable at {host}")
except Exception as exc:  # noqa: BLE001
    print(f"  [FAIL] Databricks check failed: {exc}")
    sys.exit(1)
