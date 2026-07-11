# Frontend API map

| Page | APIs |
| --- | --- |
| Login | `POST /api/auth/login`, `GET /api/auth/me`, `GET /api/auth/menus` |
| Learner profile | `GET /api/profiles/{learner_id}`, `GET /api/profiles/{learner_id}/dimensions`, `POST /api/tests/initial/submit` |
| Recognition | `POST /api/files/upload`, `POST /api/vision/recognize`, `GET /api/vision/records`, `POST /api/agent/tasks` |
| Resources | `POST /api/resources/generate`, `GET /api/resources/{resource_id}` |
| Review | `POST /api/reviews/check`, `GET /api/reviews/{resource_id}` |
| Learning path | `GET /api/learning-paths/{learner_id}`, `GET /api/reports/learning/{learner_id}` |
| AI capabilities | `GET /api/capabilities`; admin only: `POST /api/admin/model-configs/{config_id}/test` |
