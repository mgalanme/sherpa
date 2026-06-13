# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "2"
# dependencies = [
#   "sentence-transformers",
#   "einops",
#   "qdrant-client>=1.12.0",
# ]
# ///
# MAGIC %md
# MAGIC # SHERPA 03 - Gold and precomputed embeddings
# MAGIC Builds the gold place-fact table and precomputes embeddings, then upserts them into
# MAGIC Qdrant Cloud so the deployed Streamlit app does not need to embed documents at runtime.
# MAGIC Reads QDRANT_URL and QDRANT_API_KEY from the 'sherpa' secret scope.

# COMMAND ----------

# MAGIC %pip install sentence-transformers einops qdrant-client>=1.12.0

# COMMAND ----------

# MAGIC %restart_python

# COMMAND ----------

import uuid
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

CATALOG, SCHEMA = "sherpa", "pilot"
COLLECTION = "place_facts"
DIM = 768

QDRANT_URL = dbutils.secrets.get("sherpa", "QDRANT_URL")        # noqa: F821
QDRANT_API_KEY = dbutils.secrets.get("sherpa", "QDRANT_API_KEY")  # noqa: F821

silver = spark.table(f"{CATALOG}.{SCHEMA}.silver_place_poi")    # noqa: F821
gold = silver.groupBy("place", "lat", "lon").agg(
    __import__("pyspark.sql.functions", fromlist=["collect_set"]).collect_set("poi").alias("pois"))
(gold.write.format("delta").mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{CATALOG}.{SCHEMA}.gold_place"))

# COMMAND ----------

model = SentenceTransformer("nomic-ai/nomic-embed-text-v1", trust_remote_code=True)
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)

names = {c.name for c in client.get_collections().collections}
if COLLECTION not in names:
    client.create_collection(COLLECTION, vectors_config=VectorParams(size=DIM, distance=Distance.COSINE))

points = []
for row in spark.table(f"{CATALOG}.{SCHEMA}.gold_place").collect():  # noqa: F821
    text = f"{row['place']}: " + ", ".join(row["pois"] or [])
    vec = model.encode([f"search_document: {text}"], normalize_embeddings=True)[0].tolist()
    points.append(PointStruct(id=str(uuid.uuid4()), vector=vec,
                              payload={"place": row["place"], "lat": row["lat"], "lon": row["lon"],
                                       "pois": row["pois"], "text": text}))

if points:
    client.upsert(collection_name=COLLECTION, points=points)
print("Upserted", len(points), "place-fact vectors into Qdrant Cloud")
