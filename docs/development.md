# Development

先复制 `backend/.env.example` 为 `.env`，保持所有模式为 `mock`。开发版任务执行器使用 `asyncio.create_task`，未来可替换为 Redis 队列而不影响 API 或工作流协议。不要提交 `.env`、虚拟环境和 `/data` 内的上传内容。
