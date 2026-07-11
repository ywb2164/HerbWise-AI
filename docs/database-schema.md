# V0.2 database schema

迁移链：`5f85f9852819`（V0.1 初始表）→ `53e14d9e3d7c`（V0.2 业务表）。禁止修改已经执行的初始迁移。

- 认证权限：`users`、`roles`、`permissions`、`menus`、`user_roles`、`role_permissions`、`role_menus`、`refresh_tokens`。
- 画像题库：`learner_profiles`、`learner_dimensions`、`learner_weak_points`、`learner_history`、`initial_tests`、`test_questions`、`test_options`、`test_records`、`test_answers`。
- 药材知识：`medicine_items`、`medicine_aliases`、`medicine_features`、`similar_medicines`、`knowledge_sources`、`knowledge_chunk_mappings`。
- 资源审核：`resource_outputs`、`quiz_questions`、`prompt_templates`、`resource_reviews`。
- 学习报告：`learning_answers`、`learning_tasks`、`learning_paths`、`path_reports`、`report_records`。
- 后台指标：`model_configs`、`agent_configs`、`system_configs`、`test_cases`、`metric_records`。
- 基础追踪：`task_records`、`task_events`、`agent_logs`、`trace_records`、`uploaded_files`。

联合唯一约束覆盖用户/角色关联、角色/权限关联、角色/菜单关联、学习者维度、题目选项、测试答案、相似药材和路径版本。JSON 字段在 MySQL 中使用原生 JSON；时间字段使用带时区的应用层 ISO 8601 表示。
