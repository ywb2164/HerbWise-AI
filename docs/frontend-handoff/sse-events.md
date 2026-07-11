# SSE

Connect to `/api/agent/tasks/{task_id}/stream`. Render ordered `event`, `node`, `status`, `progress`, `elapsed_ms`, `summary`, and timestamp. Treat disconnect as reconnectable; never expect prompts, keys, raw documents or base64 in an event.
