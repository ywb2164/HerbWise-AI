# 个性化学习规划智能体（第二批）

## 改造前与改造后

第一批闭环从真实题库创建 `LearningTask`，服务端判分并更新画像，再推荐下一任务。第二批在不改动这些判分和画像更新规则的前提下，新增日计划：画像快照 → 受约束的计划建议 → 确定性校验 → 真实任务绑定 → 审计保存。

## LangGraph 节点

`load_context → analyze_profile → generate_plan → validate_plan → repair_plan? → bind_learning_tasks → persist_plan → save_trace`。

`repair_plan` 仅在首次校验失败时执行一次；第二次失败不会写入计划或伪造任务。图在 `backend/app/workflows/learning_plan_graph.py`，与原识别工作流独立。

## 上下文与模型协议

服务端有界读取六维得分、未解决薄弱点、最近 10 个完成任务、最近 20 条错题、待办任务、完成数及近期正确率。上下文不含 JWT、密码、Token、完整用户资料或整表数据。

模型只能返回 `LearningPlanProposal`：阶段、摘要、目标、每日分钟数和 1–5 个项目。项目含标题、原因、真实维度 code、知识点、任务类型、难度、分钟数和资源类型；不允许 task/resource/database ID。Prompt 版本为 `learning-plan-v1`。

## 确定性校验与回退

`PlanValidationService` 校验项目数量、非空字段、系统维度、任务/资源白名单、难度、5–60 分钟范围、总时长、重复知识点及待办任务重复。路由在进入工作流前执行 `ensure_learner_access`。

当 `LLM_MODE=mock` 或模型调用失败，使用确定性回退：选最低维度及其最严重薄弱点，按近期正确率选难度，并标记 `data_source=deterministic_fallback` 与 `fallback_used=true`。不会调用真实模型 API 或返回 500。

## 数据与接口

新增 `learning_plans`、`learning_plan_items`，迁移为 `f3a4b5c6d7e8_add_personalized_learning_plans.py`。计划保留画像、薄弱点、近期表现快照、模型/提示词元数据和回退标记；计划项保留目标和关联任务/资源。

- `POST /api/learning-plans/generate`
- `GET /api/learning-plans?learner_id=...`
- `GET /api/learning-plans/current?learner_id=...`
- `GET /api/learning-plans/{plan_id}?learner_id=...`
- `POST /api/learning-plans/{plan_id}/activate?learner_id=...`
- `POST /api/learning-plans/{plan_id}/cancel?learner_id=...`

任务绑定先复用同一学生的 matching pending/in-progress 真任务；若没有，只从现有真实题库创建带题目的任务。无匹配题目时计划项保持未关联，不伪造题目。

## 前端、Trace、测试

学习任务页顶部显示今日计划、目标、摘要、总时长、完成进度、项目详情和开始/继续/结果操作。无关联题目会显示明确说明，页面不显示 prompt、密钥或内部错误。

`TraceRecord` 保存每个节点的脱敏输入/输出摘要、提供商/模型元数据、耗时、重试数、数据来源、回退原因和错误码。新增 `backend/tests/test_learning_plan_contract.py` 覆盖非法维度、难度、任务类型、空/超时计划及回退选择；真实 AI 测试默认仍关闭。

已知限制：本版不接入 RAG、自动资源生成、教师审批、报告导出或 SSE。后续资源智能体应消费已验证的计划项和 `resource_type`，并保持资源审核与计划生成分离。
