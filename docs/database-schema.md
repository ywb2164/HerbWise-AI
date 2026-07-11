# V0.4.1 database schema

Migration chain: `5f85f9852819` → `53e14d9e3d7c` → `7a3e91b4c2f0` → `9c2d7e5b104a` → `c4b8e2d1a650` → `d8f7a3c209b1` → `e4d1b8f0c692` → `b9f2c8d04a71` (head). Applied revisions are immutable; deploy with `alembic upgrade head` and inspect with `alembic current`.

- Identity/RBAC: `users`, `roles`, `permissions`, `menus`, link tables and `refresh_tokens`.
- Learner and assessment: `learner_profiles`, dimensions, weak points, history, initial tests/questions/options/records/answers.
- Herbal knowledge: `medicine_items`, aliases, features, similar medicines, `knowledge_sources`, `knowledge_chunk_mappings`.
- Task and trace: `uploaded_files`, `task_records`, `task_events`, `agent_logs`, `trace_records`, `recognition_records`, `model_call_records`.
- RAG/document evidence: `knowledge_datasets`, `knowledge_documents`, `knowledge_sync_records`, `rag_retrieval_records`, `rag_evidence_records`, `rag_replay_records`. Evidence retains document/chunk/page/citation summaries; replay stores bounded cited snapshots.
- Resource, review and learning: `resource_outputs`, `quiz_questions`, `prompt_templates`, `resource_reviews`, `learning_answers`, `learning_tasks`, `learning_paths`, `path_reports`, `report_records`.
- Administration and metrics: `model_configs`, `agent_configs`, `system_configs`, `test_cases`, `metric_records`.

`report_records.output_path` is a safe relative DOCX path below `REPORT_OUTPUT_DIR`. JSON fields retain structured summaries, not credentials, raw prompts, image Base64, model weights or complete upstream responses.
