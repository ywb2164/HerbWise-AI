# API conventions

应用异常返回 `code`、`message`、`data`、`request_id`，并携带 `X-Request-ID` 响应头。时间字段使用带时区 ISO 8601。主要接口：`GET /`、`GET /health`、`GET /ready`、`POST /api/files/upload`、`POST /api/agent/tasks` 及任务查询、事件、日志、SSE 端点。
