# Workflow

`load_profile → recognize_image → vision_review → retrieve_knowledge → judge_result → generate_resources → review_resources → update_learning_path → save_trace`

审核为 `reject` 时允许重新生成一次；每个节点开始/结束写入 `task_events`，结束时写入 `agent_logs`。任务最终写入 `task_records`，完整状态写入 `trace_records`。SSE 读取已持久化事件，因此客户端断开不会取消任务。
