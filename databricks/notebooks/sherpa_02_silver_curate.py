# Databricks notebook source
# MAGIC %md
# MAGIC # SHERPA 02 - Silver curate
# MAGIC Standardises the raw bronze payloads into clean, typed place-fact rows.

# COMMAND ----------

import json
from pyspark.sql import Row

CATALOG, SCHEMA = "sherpa", "pilot"
bronze = spark.table(f"{CATALOG}.{SCHEMA}.bronze_place_raw")   # noqa: F821

rows = []
for r in bronze.collect():
    try:
        data = json.loads(r["payload"])
        pages = data.get("query", {}).get("geosearch", [])
    except Exception:
        pages = []
    for p in pages:
        rows.append(Row(place=r["place"], lat=r["lat"], lon=r["lon"],
                        poi=p.get("title", ""), source="wikipedia",
                        ingested_at=r["ingested_at"]))

if rows:
    silver = spark.createDataFrame(rows).dropDuplicates(["place", "poi"])  # noqa: F821
    (silver.write.format("delta").mode("overwrite")
           .option("overwriteSchema", "true")
           .saveAsTable(f"{CATALOG}.{SCHEMA}.silver_place_poi"))
    print("Silver rows:", silver.count())
else:
    print("No silver rows produced.")
