# V0.3A local verification

Run `uv run pytest`, `uv run ruff format --check .`, `uv run ruff check .`,
`uv run mypy app`, and `uv run python scripts/smoke_v03a_fake.py` from
`backend`. The optional real smoke requires explicit environment configuration
and is otherwise `SKIPPED`.

The current Codex runtime cannot access the user's Docker/WSL instance. Verify
the migration locally with `docker compose exec api uv run alembic upgrade head`
and then run the Fake smoke. No RAGFlow or video-stream recognition is included
in V0.3A.
