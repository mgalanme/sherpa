# Databricks notebook source
# MAGIC %md
# MAGIC # SHERPA 04 - Weekly Refresh
# MAGIC
# MAGIC Orchestrates the full Medallion pipeline in a single notebook run:
# MAGIC `01_bronze_ingest` → `02_silver_curate` → `03_gold_embeddings`
# MAGIC
# MAGIC Designed to run as a **scheduled Databricks Job** (recommended: every Monday at 07:00 CET,
# MAGIC matching the ARCAS pattern already established on this workspace).
# MAGIC
# MAGIC What it does:
# MAGIC - Extends the seed list with any new locations found in recent audit events
# MAGIC   (places that users have actually planned outings to, so enrichment is demand-driven)
# MAGIC - Re-ingests Wikipedia, Wikidata, iNaturalist and GBIF for all seeds
# MAGIC - Curates and deduplicates the silver layer
# MAGIC - Recomputes gold aggregations and upserts updated embeddings into Qdrant Cloud
# MAGIC
# MAGIC All credentials are read from the 'sherpa' Databricks secret scope.
# MAGIC No secrets are hardcoded in this notebook.

# COMMAND ----------

import datetime
import json

CATALOG = "sherpa"
SCHEMA  = "pilot"
RUN_TS  = datetime.datetime.utcnow().isoformat()

print(f"Weekly refresh started at {RUN_TS} UTC")

# COMMAND ----------
# MAGIC %md ## 1. Extend seed list from recent audit events
# MAGIC
# MAGIC Users submit activity start points through the app. We extract those coordinates
# MAGIC from the last 7 days of audit events and add them as new seeds so that places
# MAGIC people actually plan outings to get enriched automatically.

from pyspark.sql import Row  # noqa: E402
import ast  # noqa: E402

try:
    recent_events = spark.sql(f"""  # noqa: F821
        SELECT payload FROM {CATALOG}.{SCHEMA}.audit_event
        WHERE action = 'submit_inputs'
          AND ts >= '{(datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat()}'
    """).collect()

    new_seeds: list[tuple[str, float, float]] = []
    for row in recent_events:
        try:
            payload = json.loads(row["payload"])
            start = payload.get("activity_start", {})
            label = start.get("label", "")
            lat   = start.get("lat", 0.0)
            lon   = start.get("lon", 0.0)
            if label and lat and lon and abs(lat) > 0.001:
                new_seeds.append((label, float(lat), float(lon)))
        except Exception:
            continue

    print(f"New seeds from recent activity: {len(new_seeds)}")
    for s in new_seeds:
        print(f"  {s[0]} ({s[1]:.4f}, {s[2]:.4f})")

except Exception as exc:
    print(f"Could not read audit events (table may be empty on first run): {exc}")
    new_seeds = []

# COMMAND ----------
# MAGIC %md ## 2. Static seed list (always enriched)
# MAGIC
# MAGIC These are the baseline locations that are always refreshed regardless of user activity.
# MAGIC Extend this list as the pilot grows.

STATIC_SEEDS: list[tuple[str, float, float]] = [
    ("Sierra de Guadarrama", 40.78, -3.96),
    ("Cercedilla",           40.74, -4.05),
    ("El Escorial",          40.58, -4.14),
    ("Valle de Lozoya",      40.93, -3.78),
    ("Navacerrada",          40.77, -4.01),
    ("Rascafría",            40.89, -3.86),
    ("La Pedriza",           40.70, -3.87),
    ("Puerto de Cotos",      40.84, -3.97),
    ("Manzanares el Real",   40.72, -3.87),
    ("Somosierra",           41.13, -3.58),
]

# Merge static + dynamic seeds, deduplicating by label
all_seeds_map: dict[str, tuple[str, float, float]] = {s[0]: s for s in STATIC_SEEDS}
for s in new_seeds:
    if s[0] not in all_seeds_map:
        all_seeds_map[s[0]] = s
all_seeds = list(all_seeds_map.values())
print(f"Total seeds for this run: {len(all_seeds)}")

# COMMAND ----------
# MAGIC %md ## 3. Bronze ingest
# MAGIC
# MAGIC Ingests Wikipedia geosearch, iNaturalist research-grade observations,
# MAGIC and GBIF occurrences for every seed.

import requests  # noqa: E402
import time      # noqa: E402

USER_AGENT = "SHERPA-pilot/0.1 (weekly-refresh; contact: admin@sherpa-pilot.example.com)"
bronze_rows = []

for (name, lat, lon) in all_seeds:
    # Wikipedia geosearch
    try:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "geosearch",
                    "gscoord": f"{lat}|{lon}", "gsradius": 8000,
                    "gslimit": 8, "format": "json"},
            headers={"User-Agent": USER_AGENT}, timeout=30,
        )
        bronze_rows.append(Row(place=name, lat=lat, lon=lon, source="wikipedia_geosearch",
                               status=r.status_code, payload=r.text, ingested_at=RUN_TS))
    except Exception as exc:
        bronze_rows.append(Row(place=name, lat=lat, lon=lon, source="wikipedia_geosearch",
                               status=-1, payload=str(exc), ingested_at=RUN_TS))

    # iNaturalist research-grade observations
    try:
        r = requests.get(
            "https://api.inaturalist.org/v1/observations",
            params={"lat": lat, "lng": lon, "radius": 10,
                    "quality_grade": "research", "per_page": 30},
            headers={"User-Agent": USER_AGENT}, timeout=20,
        )
        bronze_rows.append(Row(place=name, lat=lat, lon=lon, source="inaturalist",
                               status=r.status_code, payload=r.text, ingested_at=RUN_TS))
    except Exception as exc:
        bronze_rows.append(Row(place=name, lat=lat, lon=lon, source="inaturalist",
                               status=-1, payload=str(exc), ingested_at=RUN_TS))

    # GBIF occurrences
    try:
        r = requests.get(
            "https://api.gbif.org/v1/occurrence/search",
            params={"decimalLatitude": f"{lat-0.1},{lat+0.1}",
                    "decimalLongitude": f"{lon-0.1},{lon+0.1}",
                    "limit": 40, "hasCoordinate": "true",
                    "basisOfRecord": "HUMAN_OBSERVATION"},
            headers={"User-Agent": USER_AGENT}, timeout=30,
        )
        bronze_rows.append(Row(place=name, lat=lat, lon=lon, source="gbif",
                               status=r.status_code, payload=r.text, ingested_at=RUN_TS))
    except Exception as exc:
        bronze_rows.append(Row(place=name, lat=lat, lon=lon, source="gbif",
                               status=-1, payload=str(exc), ingested_at=RUN_TS))

    time.sleep(1)   # be polite to all APIs

bronze_df = spark.createDataFrame(bronze_rows)  # noqa: F821
(bronze_df.write.format("delta").mode("append")
          .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_place_raw"))
print(f"Bronze: appended {bronze_df.count()} rows")

# COMMAND ----------
# MAGIC %md ## 4. Silver curate

import json as _json  # noqa: E402

silver_rows = []
# Process only the rows ingested in this run
this_run_bronze = spark.sql(f"""  # noqa: F821
    SELECT * FROM {CATALOG}.{SCHEMA}.bronze_place_raw
    WHERE ingested_at = '{RUN_TS}' AND status = 200
""").collect()

for row in this_run_bronze:
    try:
        data = _json.loads(row["payload"])
    except Exception:
        continue

    if row["source"] == "wikipedia_geosearch":
        pages = data.get("query", {}).get("geosearch", [])
        for p in pages:
            silver_rows.append(Row(place=row["place"], lat=row["lat"], lon=row["lon"],
                                   poi=p.get("title", ""), source="wikipedia",
                                   ingested_at=RUN_TS))

    elif row["source"] == "inaturalist":
        for obs in data.get("results", []):
            taxon = obs.get("taxon") or {}
            name = taxon.get("preferred_common_name") or taxon.get("name")
            if name:
                silver_rows.append(Row(place=row["place"], lat=row["lat"], lon=row["lon"],
                                       poi=name, source="inaturalist", ingested_at=RUN_TS))

    elif row["source"] == "gbif":
        for occ in data.get("results", []):
            name = occ.get("species") or occ.get("scientificName")
            if name:
                silver_rows.append(Row(place=row["place"], lat=row["lat"], lon=row["lon"],
                                       poi=name, source="gbif", ingested_at=RUN_TS))

if silver_rows:
    silver_df = (spark.createDataFrame(silver_rows)  # noqa: F821
                      .dropDuplicates(["place", "poi"]))
    (silver_df.write.format("delta").mode("append")
              .saveAsTable(f"{CATALOG}.{SCHEMA}.silver_place_poi"))
    print(f"Silver: appended {silver_df.count()} deduplicated rows")
else:
    print("Silver: no rows to append this run")

# COMMAND ----------
# MAGIC %md ## 5. Gold + embeddings → Qdrant Cloud

# MAGIC %pip install sentence-transformers==3.0.1 einops qdrant-client==1.12.4 --quiet

from sentence_transformers import SentenceTransformer  # noqa: E402
from qdrant_client import QdrantClient                  # noqa: E402
from qdrant_client.models import Distance, PointStruct, VectorParams  # noqa: E402
import uuid as _uuid  # noqa: E402

QDRANT_URL     = dbutils.secrets.get("sherpa", "QDRANT_URL")      # noqa: F821
QDRANT_API_KEY = dbutils.secrets.get("sherpa", "QDRANT_API_KEY")  # noqa: F821
COLLECTION     = "place_facts"
DIM            = 768

# Rebuild gold from the full silver table (complete history, not just this run)
gold_df = (
    spark.table(f"{CATALOG}.{SCHEMA}.silver_place_poi")  # noqa: F821
         .groupBy("place", "lat", "lon")
         .agg(__import__("pyspark.sql.functions", fromlist=["collect_set"])
              .collect_set("poi").alias("pois"))
)
(gold_df.write.format("delta").mode("overwrite")
              .option("overwriteSchema", "true")
              .saveAsTable(f"{CATALOG}.{SCHEMA}.gold_place"))
print(f"Gold: {gold_df.count()} place rows")

# Embed and upsert
model  = SentenceTransformer("nomic-ai/nomic-embed-text-v1", trust_remote_code=True)
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)

existing = {c.name for c in client.get_collections().collections}
if COLLECTION not in existing:
    client.create_collection(COLLECTION,
                             vectors_config=VectorParams(size=DIM, distance=Distance.COSINE))

points = []
for row in gold_df.collect():
    text = f"{row['place']}: " + ", ".join(row["pois"] or [])
    vec  = model.encode([f"search_document: {text}"], normalize_embeddings=True)[0].tolist()
    points.append(PointStruct(
        id=str(_uuid.uuid4()), vector=vec,
        payload={"place": row["place"], "lat": row["lat"], "lon": row["lon"],
                 "pois": row["pois"], "text": text, "refreshed_at": RUN_TS},
    ))

if points:
    client.upsert(collection_name=COLLECTION, points=points)
    print(f"Qdrant: upserted {len(points)} place-fact vectors")
else:
    print("Qdrant: nothing to upsert")

# COMMAND ----------
# MAGIC %md ## 6. Summary

print(f"""
Weekly refresh complete
  Run timestamp : {RUN_TS}
  Seeds         : {len(all_seeds)} ({len(new_seeds)} from recent user activity)
  Bronze rows   : {bronze_df.count()} appended
  Gold places   : {gold_df.count()}
  Qdrant vectors: {len(points)} upserted
""")
