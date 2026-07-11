# Development

先复制 `backend/.env.example` 为 `.env`，保持所有模式为 `mock`。开发版任务执行器使用 `asyncio.create_task`，未来可替换为 Redis 队列而不影响 API 或工作流协议。不要提交 `.env`、虚拟环境和 `/data` 内的上传内容。

V0.3A 迁移头为 `9c2d7e5b104a`。迁移后连续执行两次 `uv run python scripts/seed_data.py` 验证幂等性，再运行 `pytest`、`ruff format --check .`、`ruff check .`、`mypy app`、`scripts/export_openapi.py`、`scripts/smoke_v02.py` 和 `scripts/smoke_v03a_fake.py`。真实 API smoke 必须由用户显式配置后运行。
