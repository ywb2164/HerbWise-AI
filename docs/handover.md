# Handover

启动 Docker Desktop 后，先运行 `docker compose config`、`docker compose up -d --build`、`docker compose ps`。然后生成初始 Alembic revision、迁移、seed，并执行测试与 Ruff。真实 Qwen/Qwen-VL/RAGFlow/YOLO 只需分别实现 `LLMProvider`、`VisionProvider`、`RAGProvider` 并更新工厂；不要把凭据写入仓库。

V0.2 已提供 `docs/openapi.json`、`docs/frontend-api-map.md`、`docs/enums.md`、`docs/error-codes.md` 和 `docs/mock/*.json`。测试账号为 `admin` / `HerbWise@2026` 与 `student` / `HerbWise@2026`。当前所有 AI、视觉、RAG 和质量指标仍为 Mock/非正式数据；V0.3 推荐按 OpenAI 兼容客户端、Qwen-VL、名称归一化、RAGFlow、生成/二次审核、YOLO/ONNX 的顺序接入。
