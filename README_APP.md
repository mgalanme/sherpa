# SHERPA - Application Code Package

This package contains the application source code for the SHERPA pilot. It is deployed on top of
the Setup package (which created /home/pruebas/formacion/sherpa, the virtual environments and the
cloud connectivity).

## Layout
- `src/` application source (config, models, catalog, llm, embeddings, intake, recommend, audit,
  dossier, mesh; `clients/` open-data clients; `stores/` Qdrant, Neo4j, Databricks; `agents/`
  LangGraph orchestration and the narrative crew; `portal/` the Streamlit app)
- `databricks/notebooks/` the Medallion notebooks (bronze, silver, gold + precomputed embeddings)
- `prompts/` the master prompts
- `.streamlit/secrets.toml.example` the exact Streamlit Cloud secrets
- `scripts/` the application deploy and run scripts (20, 21, 22)

## Order
1. Extract this ZIP into `/home/pruebas/Descargas` and run `bash scripts/20_deploy_app.sh`.
2. In Databricks, run notebooks `01 -> 02 -> 03` to build the gold table and upsert place-fact
   vectors into Qdrant Cloud.
3. `bash scripts/21_seed_stores.sh` to create the Qdrant collection and Neo4j constraints.
4. Local run: `bash scripts/22_run_local.sh`. Cloud run: deploy the repo to Streamlit Community
   Cloud with `requirements.txt` equal to `requirements-cloud.txt` and the secrets from
   `.streamlit/secrets.toml.example`.

The full design and the exact secrets are described in the Application Code Guide (.docx).
