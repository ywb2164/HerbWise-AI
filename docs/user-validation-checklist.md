# User validation checklist

Run A (no real services): `scripts/verify-backend.ps1`, then open Swagger and verify mock task, replay smoke and Word report download.

Run B (RAGFlow): configure `backend/.env`, run `infra/ragflow/start-ragflow.ps1`, `uv run python scripts/ragflow_doctor.py --all`, register an authorised document, sync once, check it, then verify citations.

Run C (models/local/full loop): set the explicit `REAL_*_TESTS_ENABLED` flags and paths, then run `scripts/verify-real-services.ps1`. Capture a successful task with `capture_demo_replay.py`, verify it, set `RAG_MODE=replay`, and rerun the offline demo. Export both Word reports and inspect their source labels.

Run D (CI): push the branch and confirm backend-ci is green. Docker, credentials, local weights and authorised documents are user-owned validation inputs.
