# 药材辨识与智能辅助的安全解耦

## 调用链

改造前，`RecognitionView` 上传文件后创建 `full_loop`。该工作流依次运行学情、图像辨识、知识检索、资源生成、审核与学习路径更新；任何后续节点异常都会将同一任务置为失败，页面随之遮蔽已完成的辨识结果。

改造后，学生端调用 `POST /vision/recognize`：上传图片 → 主视觉辨识与辅助参考并行 → 名称规范化 → 知识包精确匹配 → 保存 `RecognitionRecord` → 返回 `final_identification`。该链不调用 RAG、资源生成或学习路径更新。

`full_loop`、`AgentTask`、Replay、Trace 及管理端接口继续保留，属于 legacy 兼容入口，不再是学生辨识页的默认路径。

## 状态边界

识别响应使用 `recognition_status`，成功时为 `completed`，并立即返回 `status: success` 和 `final_identification`。智能辅助使用独立 `agent_status`：`not_started`、`pending`、`running`、`completed`、`failed` 或 `skipped`。

智能辅助任务只读取 `RecognitionRecord` 快照，生成学习建议、`TaskEvent`、`AgentLog` 与独立 Trace。它不会修改药材名称、置信度、`final_identification` 或识别记录状态；失败仅显示“学习建议暂时生成失败，不影响识别结果”。

## 名称与知识包

主视觉协议同时返回 `name_zh` 和 `name_en`。`name_zh` 是目录外药材的显示名称；知识包命中后，`display_name_zh` 与 `standard_name_zh` 使用知识包标准中文名。

知识包按中文标准名、别名、训练类名、英文标准名、药典拉丁名和英文别名进行大小写/空白/标点规范化后的精确匹配，不使用模糊匹配、拼音猜测或辅助模型强制映射。目录外结果返回 `catalog_status: out_of_catalog`，不是 `Medicine not found`。

## 配置与兼容

`RECOGNITION_AGENT_MODE` 默认 `manual`：

- `off`：识别后不创建智能辅助任务。
- `manual`：用户点击“生成学习建议”后创建独立任务。
- `async`：识别完成后创建后台任务；识别响应不等待它。

`RECOGNITION_USE_LEGACY_FULL_LOOP=false` 是默认兼容开关；旧 full-loop 接口仍保留给 Replay、演示和管理端。

## 前端与错误处理

RecognitionView 只展示“本草智策智能辨识引擎”等产品文案，不展示供应商、模型名或工作流实现名称。识别进度只包括上传、智能辨识、名称与知识核验和保存结果；学习建议单独显示。

主视觉不可用显示服务不可用；无法辨识提示更换清晰图片；知识包目录外显示中文识别名与本地知识库未收录提示。辅助参考、RAG、资源生成和学习路径失败均不覆盖识别结果。

## Trace 与限制

智能辅助 Trace 保存 `recognition_id`，与其独立任务关联。当前持久化 Trace 表没有 `parent_trace_id` 列，因此父链以 Trace JSON 字段保存；后续可通过单独迁移将其提升为可查询字段。

测试不调用真实模型 API。已覆盖：独立识别响应、中文主标题数据、目录外建议与默认智能辅助配置；仍需由用户用真实图片完成页面验收。
