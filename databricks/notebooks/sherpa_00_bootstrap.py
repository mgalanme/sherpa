# Databricks notebook source
# MAGIC %md
# MAGIC # SHERPA 00 - Bootstrap
# MAGIC
# MAGIC **Run once** before any other notebook or before the first app use.
# MAGIC Creates the Unity Catalog catalogue, schema, and all Delta tables required by SHERPA.
# MAGIC Safe to re-run: all statements use `IF NOT EXISTS`.
# MAGIC
# MAGIC Prerequisites:
# MAGIC - The Databricks workspace is the one configured in the app secrets
# MAGIC   (`DATABRICKS_HOST`, `DATABRICKS_HTTP_PATH`).
# MAGIC - The executing principal has `CREATE CATALOG` privilege, or the catalogue already exists
# MAGIC   and the principal has `USE CATALOG` and `CREATE SCHEMA` on it.
# MAGIC - The 'sherpa' secret scope exists (created during pilot setup via `10_databricks_bootstrap.sh`).

# COMMAND ----------

CATALOG = "sherpa"
SCHEMA  = "pilot"

# COMMAND ----------
# MAGIC %md ## 1. Catalogue and schema

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")  # noqa: F821
spark.sql(f"USE CATALOG {CATALOG}")                   # noqa: F821
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")    # noqa: F821
spark.sql(f"USE SCHEMA {SCHEMA}")                     # noqa: F821
print(f"Catalogue '{CATALOG}' and schema '{SCHEMA}' ready.")

# COMMAND ----------
# MAGIC %md ## 2. Audit trail table (append-only, hash-chained)
# MAGIC
# MAGIC This table is written by `src/audit.py` at runtime.
# MAGIC The explicit column list is critical: Delta MERGE and INSERT operations
# MAGIC must never rely on schema inference to avoid contamination across runs.

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.audit_event (
  event_id  STRING  NOT NULL COMMENT 'UUID of this audit event',
  ts        STRING  NOT NULL COMMENT 'ISO-8601 UTC timestamp',
  actor     STRING  NOT NULL COMMENT 'user | system | reviewer',
  action    STRING  NOT NULL COMMENT 'submit_inputs | draft_ready | hitl_decision | pdf_generated | ...',
  plan_id   STRING  NOT NULL COMMENT 'Identifier of the planning session',
  payload   STRING           COMMENT 'JSON payload of the event',
  prev_hash STRING           COMMENT 'SHA-256 hash of the previous event (chain anchor)',
  hash      STRING           COMMENT 'SHA-256 hash of this event concatenated with prev_hash'
)
USING DELTA
COMMENT 'Append-only, hash-chained audit trail for all SHERPA actions.'
TBLPROPERTIES (
  'delta.appendOnly' = 'true',
  'sherpa.version'   = '1'
)
""")  # noqa: F821
print("audit_event table ready.")

# COMMAND ----------
# MAGIC %md ## 3. Bronze raw ingestion table

spark.sql(f"""  # noqa: F821
CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.bronze_place_raw (
  place        STRING  COMMENT 'Seed place name',
  lat          DOUBLE  COMMENT 'Latitude of the seed point',
  lon          DOUBLE  COMMENT 'Longitude of the seed point',
  source       STRING  COMMENT 'API source identifier',
  status       INT     COMMENT 'HTTP status code of the raw call',
  payload      STRING  COMMENT 'Raw JSON response body',
  ingested_at  STRING  COMMENT 'ISO-8601 UTC ingestion timestamp'
)
USING DELTA
COMMENT 'Bronze layer: raw responses from open-data APIs (Wikipedia, iNaturalist, GBIF, etc.).'
""")
print("bronze_place_raw table ready.")

# COMMAND ----------
# MAGIC %md ## 4. Silver curated POI table

spark.sql(f"""  # noqa: F821
CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.silver_place_poi (
  place        STRING  COMMENT 'Place name (from seed)',
  lat          DOUBLE,
  lon          DOUBLE,
  poi          STRING  COMMENT 'Point of interest or species name',
  source       STRING  COMMENT 'wikipedia | inaturalist | gbif | wikidata',
  ingested_at  STRING
)
USING DELTA
COMMENT 'Silver layer: standardised, deduplicated place-POI pairs.'
""")
print("silver_place_poi table ready.")

# COMMAND ----------
# MAGIC %md ## 5. Gold place table

spark.sql(f"""  # noqa: F821
CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.gold_place (
  place  STRING  COMMENT 'Place name',
  lat    DOUBLE,
  lon    DOUBLE,
  pois   ARRAY<STRING> COMMENT 'Aggregated POI list for this place'
)
USING DELTA
COMMENT 'Gold layer: one row per place with aggregated POIs, ready for embedding.'
""")
print("gold_place table ready.")

# COMMAND ----------
# MAGIC %md ## 6. Verify

tables = spark.sql(f"SHOW TABLES IN {CATALOG}.{SCHEMA}").collect()  # noqa: F821
print(f"\nTables in {CATALOG}.{SCHEMA}:")
for row in tables:
    print(f"  {row['tableName']}")

print("\nBootstrap complete. You can now run notebooks 01 → 02 → 03 for the initial data load,")
print("and configure the weekly job (sherpa_04_weekly_refresh) in Databricks Workflows.")
