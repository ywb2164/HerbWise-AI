# Handover

启动 Docker Desktop 后，先运行 `docker compose config`、`docker compose up -d --build`、`docker compose ps`。然后生成初始 Alembic revision、迁移、seed，并执行测试与 Ruff。真实 Qwen/Qwen-VL/RAGFlow/YOLO 只需分别实现 `LLMProvider`、`VisionProvider`、`RAGProvider` 并更新工厂；不要把凭据写入仓库。
