# API freeze V0.4

Freeze date: 2026-07-11. API prefix is `/api`; authentication is `Authorization: Bearer <access_token>`. Responses use the established envelope where documented, pagination returns `items`, `page`, `page_size`, `total`, `pages`, and errors use `code`, `message`, and request context.

Existing fields are additive-only after this freeze. Key domains are upload, task/recognition, retrieval/evidence, resources/review, trace, replay, metrics and reports. SSE is `/api/agent/tasks/{task_id}/stream`; event payloads are redacted summaries and never contain prompts, credentials, image base64 or complete upstream responses. Report APIs are `POST /api/reports/learning/{learner_id}/export-word`, `POST /api/reports/tasks/{task_id}/export-word`, and `GET /api/reports/{report_id}/download`.

Clients must show `data_source` (`mock`, `replay`, `real`, or `hybrid`), fallback and manual-review indicators rather than presenting demonstration material as an official metric or clinical conclusion.
