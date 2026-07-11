# V0.4.1 module ownership

| Module | Owns | Main API prefix |
| --- | --- | --- |
| `auth` | JWT、刷新令牌、RBAC 依赖、用户/角色/菜单模型 | `/api/auth` |
| `profiles` | 六维画像、弱点、历史、初始测试 | `/api/profiles`, `/api/tests` |
| `knowledge` | 药材、别名、特征、相似关系、来源映射 | `/api/medicines` |
| `resources` | 上传文件、资源、Prompt、审核 | `/api/files`, `/api/resources`, `/api/reviews` |
| `learning_paths` | 学习答案、路径版本、报告 | `/api/learning`, `/api/learning-paths`, `/api/reports` |
| `tasks` / `workflows` | 固定 DAG、任务、事件、Agent 日志 | `/api/agent/tasks` |
| `traces` | 可追溯工作流快照 | `/api/traces` |
| `system` | 健康检查、后台配置、指标 | `/api/admin`, `/api/metrics` |

Router 只负责 HTTP 校验和响应；Service 负责事务边界与业务规则；SQLAlchemy model 负责持久化；Provider 抽象负责外部 AI/RAG/视觉能力。跨模块调用通过 Service 和可序列化 ID，不在 WorkflowState 中保存 ORM 对象。
# V0.4 ownership

`learning_paths` owns report records and controlled DOCX export; `scripts` owns redacted diagnostics and smoke commands; `infra/ragflow` owns optional RAGFlow bootstrap wrappers; Soybean Admin frontend consumes frozen API contracts only. Its official source is pending integration and is not present in this repository.
