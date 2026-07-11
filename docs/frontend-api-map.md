# Soybean Admin frontend API map

This map is for the Soybean Admin frontend integration. Official Soybean Admin source is not yet included in this repository; the frozen backend APIs and handoff materials are ready for integration.

| Page | APIs |
| --- | --- |
| Login | `POST /api/auth/login`, `GET /api/auth/me`, `GET /api/auth/menus` |
| Learner profile | `GET /api/profiles/{learner_id}`, `GET /api/profiles/{learner_id}/dimensions`, `POST /api/tests/initial/submit` |
| Recognition | `POST /api/files/upload`, `POST /api/vision/recognize`, `GET /api/vision/records`, `POST /api/agent/tasks` |
| Resources | `POST /api/resources/generate`, `GET /api/resources/{resource_id}` |
| Review | `POST /api/reviews/check`, `GET /api/reviews/{resource_id}` |
| Learning path | `GET /api/learning-paths/{learner_id}`, `GET /api/reports/learning/{learner_id}` |
| AI capabilities | `GET /api/capabilities`; admin only: `POST /api/admin/model-configs/{config_id}/test` |
# V0.4 additions

Report export and download are available at `/api/reports/learning/{learner_id}/export-word`, `/api/reports/tasks/{task_id}/export-word`, and `/api/reports/{report_id}/download`. Soybean Admin views must expose mock/replay/real source labels and manual-review/fallback states.
