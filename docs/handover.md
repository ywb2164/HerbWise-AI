# V0.4.1 operational handoff

启动 Docker Desktop 后，运行 `docker compose config`、`docker compose up -d --build`、`docker compose ps`。数据库只执行 `alembic upgrade head` 和 `alembic current`，随后 seed 与验证；不要生成新的初始 Alembic revision。真实 Qwen/Qwen-VL/RAGFlow/YOLO 已有 Provider 适配器，凭据只通过环境变量配置，真实调用必须显式开启。

`docs/openapi.json`、`docs/frontend-api-map.md`、`docs/enums.md`、`docs/error-codes.md` 和 `docs/mock/*.json` 已交接给 Soybean Admin 前端接入。仓库尚未包含正式 Soybean Admin 源码，后端 API 与交接资料已冻结。Mock/Replay 是演示数据；真实 AI、视觉和 RAGFlow 可在完成环境配置后验证。

Use root `scripts/start-dev.ps1`, `start-demo.ps1`, `verify-backend.ps1`, `verify-real-services.ps1`, and `backup-database.ps1`. Detailed user-local commands and frontend contracts are in `pending-user-commands.md` and `frontend-handoff/`.
