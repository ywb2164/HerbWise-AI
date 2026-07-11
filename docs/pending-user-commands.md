# Copyable user-local commands

```powershell
Set-Location D:\HerbWise-AI
Copy-Item backend\.env.example backend\.env
docker compose up -d --build
Set-Location backend
uv sync
uv run alembic upgrade head
uv run alembic current
uv run python scripts/seed_data.py
uv run python scripts/seed_data.py
uv run pytest -q
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run python scripts/smoke_v03b_fake.py
uv run python scripts/evaluate_rag_retrieval.py --mode fake
uv run python scripts/smoke_demo_replay.py
uv run python scripts/smoke_degradation.py
uv run python scripts/config_doctor.py --check all
```

For real services, edit `backend/.env` with placeholders only: `RAGFLOW_BASE_URL=<URL>`, `RAGFLOW_API_KEY=<KEY>`, `RAGFLOW_DATASET_ID=<ID>`, `MODEL_API_BASE_URL=<URL>`, `MODEL_API_KEY=<KEY>`, and explicit test flags. Then run `..\infra\ragflow\start-ragflow.ps1`, `uv run python scripts/ragflow_doctor.py --all`, `uv run python scripts/ai_provider_doctor.py --all`, `uv run python scripts/local_model_doctor.py --info`, and `uv run python scripts/smoke_v03c_real.py`.

After an authorised upload: `uv run python scripts/register_knowledge_document.py <uploaded_file_id> <dataset_code>`, `uv run python scripts/sync_knowledge_document.py <document_code>`, `uv run python scripts/check_knowledge_document.py <document_code>`, `uv run python scripts/verify_rag_citations.py 黄芪 性状`.

Capture/verify replay with `uv run python scripts/capture_demo_replay.py <task_id>` and `uv run python scripts/verify_demo_replay.py <replay_code>`. Backup with `..\scripts\backup-database.ps1`; inspect logs with `docker compose logs api`; rollback only after backup using your selected stable Git tag.
