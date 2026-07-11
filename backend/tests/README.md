# Test layers

`uv run pytest` runs dependency-free unit tests for health, Mock providers and review retry routing. Database-backed upload, task API, event, trace and SSE integration tests must be run after Docker is available and the initial Alembic migration has been generated/applied. They intentionally are not faked against a production MySQL URL.
