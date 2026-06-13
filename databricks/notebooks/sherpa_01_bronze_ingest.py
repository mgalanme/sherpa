# Databricks notebook source
# MAGIC %md
# MAGIC # SHERPA 01 - Bronze ingest
# MAGIC Captures raw open-data responses with their source and timestamp into the bronze layer.
# MAGIC Run on a schedule or on demand. Reads secrets from the 'sherpa' secret scope.

# COMMAND ----------

import datetime as dt
import requests
from pyspark.sql import Row

CATALOG = dbutils.widgets.get("catalog") if dbutils.widgets.getAll() else "sherpa"  # noqa: F821
CATALOG = "sherpa"
SCHEMA = "pilot"
spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")          # noqa: F821
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")  # noqa: F821

USER_AGENT = "SHERPA-pilot/0.1 (contact: your-email@example.com)"

# COMMAND ----------

# Example bronze source: a set of seed locations to enrich with heritage facts.
# In the pilot these seeds come from a maintained reference table; here we illustrate the shape.
seeds = [
    ("Sierra de Guadarrama", 40.78, -3.96),
    ("Cercedilla", 40.74, -4.05),
]

rows = []
now = dt.datetime.utcnow().isoformat()
for name, lat, lon in seeds:
    try:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "geosearch", "gscoord": f"{lat}|{lon}",
                    "gsradius": 5000, "gslimit": 5, "format": "json"},
            headers={"User-Agent": USER_AGENT}, timeout=30)
        payload = r.text
        status = r.status_code
    except Exception as exc:  # noqa: BLE001
        payload = str(exc)
        status = -1
    rows.append(Row(place=name, lat=lat, lon=lon, source="wikipedia_geosearch",
                    status=status, payload=payload, ingested_at=now))

bronze = spark.createDataFrame(rows)                          # noqa: F821
(bronze.write.format("delta").mode("append")
       .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_place_raw"))

print("Bronze ingest complete:", bronze.count(), "rows")
