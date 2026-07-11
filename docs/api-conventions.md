# API conventions

应用异常返回 `code`、`message`、`data`、`request_id`，并携带 `X-Request-ID` 响应头。时间字段使用带时区 ISO 8601。主要接口：`GET /`、`GET /health`、`GET /ready`、`POST /api/files/upload`、`POST /api/agent/tasks` 及任务查询、事件、日志、SSE 端点。

V0.2 业务接口使用统一成功 envelope：`{"code":0,"message":"success","data":...,"request_id":"..."}`；原任务/文件成功体保持兼容。分页数据包含 `items`、`page`、`page_size`、`total`、`pages`。401 表示未认证，403 表示角色/权限不足，404 表示资源不存在，409 表示唯一约束或引用冲突。OpenAPI 操作必须具备 summary、description、tags 和适用的 Bearer security 声明。
