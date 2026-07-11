# Workflow

`load_profile → recognize_image → vision_review → retrieve_knowledge → judge_result → generate_resources → review_resources → update_learning_path → save_trace`

审核为 `reject` 时允许重新生成一次；每个节点开始/结束写入 `task_events`，结束时写入 `agent_logs`。任务最终写入 `task_records`，完整状态写入 `trace_records`。SSE 读取已持久化事件，因此客户端断开不会取消任务。

V0.2 实际任务由 runner 设置 `persistence_enabled=true`：画像优先读取数据库，知识节点优先读取 `medicine_items`/`medicine_features`，资源、审核和学习路径分别调用对应 Service，并把 `resource_ids`、`review_id`、路径版本和数据来源写入可序列化 state/trace。直接调用图的单元测试保持原 Mock 分支，以验证固定 DAG 和一次重试约束。

V0.3A keeps the node order. `recognize_image` selects Mock, Qwen, Local, or Hybrid by the optional task mode. Hybrid executes both paths concurrently, normalizes names from the database, records both raw internal results, and writes a fusion result before `vision_review` and `judge_result`.
