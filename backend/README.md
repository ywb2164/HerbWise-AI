## HerbWise AI backend

本项目是“本草智策”的可扩展 FastAPI 单体后端骨架。当前交付重点是可运行的 Mock 工作流与明确的模块边界，而非接入真实模型服务。

### 已完成能力

- FastAPI 生命周期、JSON 结构化日志、request ID、统一应用异常；
- SQLAlchemy 2.x 异步模型、Redis 异步客户端、Alembic 异步配置；
- Mock LLM、视觉和 RAG Provider，以及固定 LangGraph DAG；
- 开发版 `asyncio.create_task` 任务执行、任务事件/日志/Trace 持久化和 SSE；
- 受限图片上传和 MySQL/Redis/API 的 Docker Compose 配置。

尚未接入 Qwen、Qwen-VL、RAGFlow、YOLO、New API；这些 Provider 的边界已预留。

### 环境与启动

需要 Windows 11、Docker Desktop（WSL2 后端）和 uv。复制配置后启动：

```powershell
Copy-Item .env.example .env
Set-Location ..
docker compose up -d --build
docker compose logs -f api
```

容器健康后执行迁移和示例数据：

```powershell
docker compose exec api uv run alembic revision --autogenerate -m "initial backend framework tables"
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run python scripts/seed_data.py
```

访问 Swagger：`http://localhost:8000/docs`。存活检查为 `/health`，依赖检查为 `/ready`。

### 开发命令

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

`scripts/reset_db.py` 是危险脚本，必须显式传入 `--confirm-reset`，绝不会自动执行。

### 扩展方式

新增业务模块采用 `router.py`、`schemas.py`、`service.py`、`repository.py`、`models.py` 结构，并在 `app/api/router.py` 注册。新增工作流节点时，将独立异步函数放入 `app/workflows/nodes/`，在 `graph.py` 中接入边和条件路由。真实 Provider 应实现 `app/integrations/contracts.py` 的抽象接口，再在 `factory.py` 按环境变量选择；业务代码不得直接判断 `AI_MODE`。

Mock 模式用于本地稳定验收；Real 模式只在相应 Provider 和凭据明确配置后启用。
