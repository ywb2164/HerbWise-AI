# 学习任务改造第一批

## 改造前与改造后

改造前，`LearningTasksView` 在浏览器内维护题库、正确答案、解释和判分结果，并通过 `/learning/answers` 写入客户端传来的分数。`learning_tasks` 只是学习路径推荐条目。画像的六维能力、薄弱点和历史虽已持久化，但不存在一次可恢复、可审计的真实练习闭环。

改造后，`/api/learning-tasks` 是正式练习路径。服务端从 `learning_questions` 选题，任务开始时只返回题干和选项；提交时服务端验证题目归属、选项、完整性和 attempt 所有权，完成判分、持久化、画像更新、学习事件和下一任务推荐。旧的 `/learning/answers` 与 `/learning-paths/*` 保留兼容。

## 复用与数据结构

- 复用 `LearningTask`（扩展为可执行任务）、`LearnerDimension`、`LearnerWeakPoint`、`LearnerHistory`、`TaskEvent`、`TraceRecord` 和 JWT learner 隔离。
- 新增 `learning_questions`、`learning_task_questions`、`learning_task_attempts`、`learning_task_answers`、`learning_events`。
- 迁移：`f1a2b3c4d5e6_add_deterministic_learning_tasks.py`，只增量创建表/列和索引；`f2a3b4c5d6e7_merge_learning_task_heads.py` 合并既有报告分支以保持单一 head；不删除或重命名既有数据。

## API

- `GET /api/learning-tasks?learner_id=...`：分页任务列表；首次无任务时按最低维度创建 `initial_plan`。
- `GET /api/learning-tasks/{task_id}?learner_id=...`：仅返回题干、选项、维度、知识点和分值。
- `POST /api/learning-tasks/{task_id}/start?learner_id=...`：幂等地返回同一个进行中 attempt。
- `POST /api/learning-tasks/{task_id}/submit?learner_id=...`：请求体为 `{ "attempt_id": "...", "answers": [{"question_id": 1, "answer": "A"}] }`。
- `GET /api/learning-tasks/{task_id}/result?learner_id=...`：仅任务所有者（或既有员工角色）读取判分结果。

提交响应包含分数、题目结果（此时才有正确答案与解释）、六维变化、薄弱点变化和下一任务。`answer_key`、`correct_answer`、`explanation`、`is_correct` 不存在于提交前题目响应和 TypeScript 的 `LearningTaskQuestion`。

## 规则与审计

单选/判断完全匹配，分值由 `learning_task_questions.score_weight` 决定；多选按无序集合完全匹配。`raw_score` 与 `final_score` 在第一版一致，`accuracy` 为答对题数比例。已完成 attempt 重复提交直接返回首次结果，不重复更新画像或创建下一任务。

每个维度按本任务该维度正确率更新：`<.40=-3`、`<.60=-1`、`<.85=+1`、其余 `+3`，再乘难度权重（basic 0.8、intermediate 1.0、advanced 1.2），四舍五入并限制在每任务 -4 至 +4、总分 0 至 100。连续两次错误提高薄弱点严重度；连续三次正确降低严重度但不清零。

事件包括 `task_created`、`task_started`、`question_answered`、`task_completed`、`profile_updated`、`next_task_created`。同时写入 `TaskEvent`，并产生标注为 `node_type=deterministic_service`、`data_source=database`、`model=null` 的最小 Trace，不伪装为模型调用。

下一任务按本次最弱维度选择：正确率低于 0.60 使用 basic，低于 0.85 使用 intermediate，其余使用 advanced；缺题时回退到该维度的可用草稿题，仍不足则不伪造任务。

## 前端与种子

`LearningTasksView.vue` 删除了浏览器题库和本地判分，支持待完成/进行中/已完成分组、继续 attempt、提交中状态、结果恢复、画像变化和下一任务展示。`frontend/src/types/api.ts` 的未提交题型不含答案字段。

题库在 `backend/data/seed/learning_questions.json`，含六维各三题、基础/中等难度、`review_status=draft` 的演示题。运行 `backend/.venv/Scripts/python.exe backend/scripts/seed_learning_questions.py` 可重复执行并输出 `created/updated/skipped`。

## 已知限制与第二批建议

题库是竞赛演示草稿，未声称完成中药学专业终审；第一批没有教师端、RAG、LLM 或 SSE 依赖。第二批可在保持本事件契约的基础上接入经过审核的出题、资源和报告智能体，并为并发提交加入数据库级唯一/锁策略。
