# Architecture

FastAPI 单体按 `core`、`common`、`modules`、`integrations`、`workflows` 分层。HTTP 路由只负责校验和编排，持久化由 SQLAlchemy 异步会话完成。MySQL 保存任务、事件、日志、追踪、学习者与上传文件；Redis 作为可替换的运行时基础设施预留。

生产数据库连接使用 `mysql+asyncmy://...@db:3306/...`，Redis 使用 `redis://redis:6379/0`。容器数据统一挂载到 `/data`，数据库仅保存相对路径。
