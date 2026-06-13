# SHERPA - Pilot Setup Scripts

This package contains the setup scripts for the SHERPA pilot. It does not contain the
application source code, which is delivered separately.

Read the Setup document (SHERPA_Pilot_Setup_Guide.docx) and run the scripts in order.

1. Extract this ZIP into /home/pruebas/Descargas
2. bash scripts/00_deploy.sh         (copies everything to /home/pruebas/formacion/sherpa)
3. cd /home/pruebas/formacion/sherpa/scripts
4. Follow the document from section 6 onwards (01 -> 13), then 99_teardown.sh to stop.

Scripts:
  00_deploy.sh              Deploy scripts from Descargas to formacion/sherpa
  01_prereqs_check.sh       Verify local prerequisites
  02_dirs_and_env.sh        Create layout and the .env from template
  03_uv_bootstrap.sh        Ensure uv (user-space)
  04_venv_langchain.sh      Create .venv-langchain
  05_venv_crewai.sh         Create .venv-crewai
  06_venv_mesh.sh           Create .venv-mesh (Solace Agent Mesh)
  07_docker_compose_up.sh   Start local dev containers (Solace, Qdrant, Neo4j)
  08_ollama_models.sh       Pull qwen2.5:3b (local fallback)
  09_cloud_accounts_check.sh  Check cloud credentials and connectivity
  10_databricks_bootstrap.sh  Secret scope, catalog/schema, audit table
  11_solace_cloud_check.sh  Validate Solace Cloud target
  12_smoke_test.sh          End-to-end connectivity smoke tests
  13_github_sync.sh         Create/update the GitHub repo via gh
  99_teardown.sh            Stop local containers and processes
