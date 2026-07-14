# 学生端个性化学习业务前端审计

审计日期：2026-07-13；审计方式：静态代码审查、前端类型/构建验证、后端路由与实现对照。除本报告外，未修改任何业务代码、配置或提交 Git。

## 1. 审计范围与当前 commit

| 项目 | 结果 |
|---|---|
| 当前分支 | `feat/fullstack-vision-integration` |
| 当前 commit | `0469d91dbc3c33631a45c55edd76e43887c49ae4` |
| 工作区状态 | 已有用户未提交变更：README、前后端多文件及新增 `backend/app/modules/knowledge/catalog.py`；本审计未触碰这些文件。 |
| 学生端技术栈 | Vue 3、TypeScript、Vite、Vue Router、Pinia、Axios、Naive UI、ECharts。入口：[frontend/src/main.ts](../frontend/src/main.ts)，HTTP 基址 `/api`。 |
| 学生端入口 | `/login`；认证后路由壳为 `/`，默认重定向 `/dashboard`。 |
| 管理端技术栈 | 独立 Vue 3 / Vite / TypeScript Soybean Admin 应用，Pinia、Naive UI、Alova/Axios。 |
| 管理端入口 | 独立开发服务（Vite 端口 9528）；登录页会跳转统一学生端登录入口。 |

审计范围包含 `frontend/`、`admin-frontend/`、两端路由与菜单、Pinia、Axios 封装、TS 类型、页面组件、轮询/SSE、图表、认证权限及后端 `/api` 路由和服务实现。未将 README 或设计文档作为实现结论的依据。

## 2. 路由与菜单总览

| 角色 | 菜单 | 路由 | 页面文件 | 当前状态 |
|---|---|---|---|---|
| 学生 | 学习工作台 | `/dashboard` | `frontend/src/views/DashboardView.vue` | 已接画像、诊断、路径、资源接口；汇总页。 |
| 学生 | 构建学习画像 | `/onboarding` | `ProfileOnboardingView.vue` | 有初测/画像入口。 |
| 学生 | 能力诊断 | `/diagnosis` | `DiagnosisView.vue` | 有六维和薄弱点接口。 |
| 学生 | 画像档案 | `/profile` | `ProfileView.vue` | 有画像、历史和维度接口。 |
| 学生 | 药材辨识 | `/recognition` | `RecognitionView.vue` | 上传、轮询任务、结果/证据展示；当前 TypeScript 失败。 |
| 学生 | 虚拟仿真实训 | `/simulation` | `SimulationView.vue` | 非本次六页核心，需另行核验业务闭环。 |
| 学生 | 药材知识 | `/knowledge` | `KnowledgeView.vue` | 目录/详情真实接口；RAG 为用户显式触发。 |
| 学生 | 学习资源 | `/resources` | `ResourcesView.vue` | 资源 CRUD 展示与生成/审核接口。 |
| 学生 | 学习任务 | `/learning-tasks` | `LearningTasksView.vue` | 画像数据真实；练习题前端硬编码。 |
| 学生 | 学习报告 | `/reports` | `ReportsView.vue` | 可生成/导出，但学习报告内容明确为 mock。 |
| 学生 | 证据链 | `/traces` | `TracesView.vue` | 展示持久化 Trace、任务事件、日志；默认混入系统级指标。 |
| 学生 | 测试指标 | `/metrics` | `MetricsView.vue` | 数据库计数真实，质量三指标为 mock；混合学生和系统指标。 |
| 管理员 | 管理总览 | `/home` | `admin-frontend/src/herbwise/views/admin/AdminOverviewView.vue` | 已接统计、任务/日志/模型/Agent 记录。 |
| 管理员 | 用户/角色/菜单 | `/manage/user`、`/manage/role`、`/manage/menu` | `AdminUsers/ Roles/ MenusView.vue` | 通用管理 CRUD；与学生端菜单无运行时绑定证据。 |
| 管理员 | 模型服务 | `/alova/request` | `AdminModelsView.vue` | 模型配置 CRUD/连通性测试。 |
| 管理员 | 智能体编排 | `/alova/scenes` | `AdminAgentsView.vue` | Agent 配置 CRUD；固定工作流未读取此配置。 |
| 管理员 | Prompt 模板 | `/plugin/copy` | `AdminPromptsView.vue` | 模板 CRUD；资源服务可读取启用模板版本。 |
| 管理员 | 测试用例 | `/plugin/icon` | `AdminTestsView.vue` | 测试用例 CRUD，后端标为 mock evaluation cases。 |
| 管理员 | 运行日志 | `/function/request` | `AdminOperationsView.vue` | 任务记录与节点日志只读查看。 |
| 管理员 | 系统配置 | `/function/toggle-auth` | `AdminSystemView.vue` | 系统配置 CRUD；没有被业务服务读取的证据。 |

学生端路由守卫使用 token、角色和 `GET /profiles/{learner_id}` 来决定是否转到 onboarding；API 层统一加 Bearer token，并在 401 时刷新 token。学生端没有独立的路由级权限矩阵，依赖后端 `ensure_learner_access` 隔离学习者数据。管理端路由在 `admin-frontend/src/router/routes/index.ts` 显式替换 Soybean 模板视图为 HerbWise 视图，但仍保留大量无关模板路由文件。

## 3. 六个核心页面逐页审计

### 3.1 药材知识

| 项目 | 当前实现 |
|---|---|
| 路由 | `/knowledge` |
| 页面文件 | `frontend/src/views/KnowledgeView.vue` |
| 主要组件 | 目录搜索列表、详情卡、性状特征、近似药、按需“知识证据检索”面板、`SourceBadge`。 |
| 数据来源 | 目录、详情、特征、近似药来自后端数据库；检索来自 `HybridKnowledgeService`，默认配置可退化为 mock/RAG replay。 |
| 调用接口 | `GET /medicines`、`GET /medicines/{id}`、`GET /medicines/{id}/features`、`GET /medicines/{id}/similar`、显式点击后 `POST /knowledge/retrieve`。 |
| 是否使用 Agent | 否；普通浏览不调用 Agent。 |
| 是否使用 RAG | 是，但仅由“检索证据”按钮调用，不阻塞目录、详情或搜索，符合按需定位。 |
| Evidence/Citation | 检索结果展示 `evidence_id`、document、page、chunk、score、citation；目录详情本身不假装具有 RAG 依据。 |
| 加载/空/失败 | 列表和详情有 `NSpin`、空态和错误提示；检索有 loading/error toast。 |
| 是否真实可用 | **接口已接但取决于数据与 RAG 配置**；结构化知识页可用，RAG 默认模式为 mock。 |
| 主要问题 | 页面仅显示来源、性味、归经、描述、特征及近似药，未形成目标定位中的别名、产地、药用部位、完整表面/断面/气味质地、系统性质量风险字段；`SourceBadge source="mysql"` 为固定标注。 |

请求契约：列表发送 `page/page_size/keyword`，返回 `{items,page,page_size,total,pages}`；检索发送 `learner_id, medicine_name, task_type, query?, top_k`，返回 `retrieval_id/provider/dataset_id/evidences[]`。与 `backend/app/modules/knowledge/router.py`、`rag_router.py` 字段匹配。

### 3.2 学习资源

| 项目 | 当前实现 |
|---|---|
| 路由 | `/resources` |
| 页面文件 | `frontend/src/views/ResourcesView.vue` |
| 主要组件 | 资源总数/审核数统计、资源表格、生成弹窗、详情抽屉、审核结果卡。 |
| 数据来源 | 资源和审核记录持久化于后端数据库；生成服务在 mock 配置下调用 `MockLLMProvider`，可在 real/runtime 配置下选择模型。 |
| 调用接口 | `GET /resources?learner_id`、`GET /resources/{id}`、`POST /resources/generate`、`GET /reviews/{id}`、`POST /reviews/check`。 |
| 是否使用 Agent | 不直接调 Agent 任务；资源服务可记录模型调用。 |
| 是否使用 RAG | 生成接口可携带 `retrieval_id/evidence_ids`，但本页面只传 `task_id`，未主动检索，因此常走无引用的 mock evidence。 |
| Evidence/Citation | UI 不展示资源的 citations/evidence snapshot、生成来源、prompt version 或个性化依据；只展示 provider、任务 ID、审核分数。 |
| 加载/空/失败 | 有 loading、空态、toast；详情加载失败没有保留独立错误面板。 |
| 是否真实可用 | **接口已接但数据/内容完整性不足**：资源能落库、读取、审核；默认仍是 mock 内容，且页面允许任意药名/难度手工生成。 |
| 主要问题 | 没有“画像分析→资源类型选择→知识检索→生成→审核→保存”的前端闭环，生成时不读取弱项/能力维度；资源表缺目标知识点、适用维度、是否个性化、引用数量、审核来源等业务字段。 |

后端 `generate_resource()` 会保存 profile snapshot、evidence snapshot、prompt version、provider；但前端 `ResourceItem` 和详情没有把其中大部分可审计字段呈现出来。审核服务在未启用真实模型时使用确定性规则，接口描述也明确为 mock content checks。

### 3.3 学习任务

| 项目 | 当前实现 |
|---|---|
| 路由 | `/learning-tasks` |
| 页面文件 | `frontend/src/views/LearningTasksView.vue` |
| 主要组件 | 路径摘要、单题练习、答案历史、选药材和追问后生成跟进资源。 |
| 数据来源 | 路径、维度、历史答案、药材目录来自接口；题干、选项、正确答案和解释来自页面中的 `questionBank` 常量。 |
| 调用接口 | `GET /learning-paths/{learner}`、`GET /profiles/{learner}/dimensions`、`GET /learning/answers/{learner}`、`GET /medicines`、`POST /learning/answers`、`POST /learning-paths/update`；跟进资源时 `POST /knowledge/retrieve`→`POST /resources/generate`→`POST /reviews/check`。 |
| 是否使用 Agent | 没有任务规划 Agent；仅在跟进资源的服务层可能使用模型。 |
| 是否使用 RAG | 只在“生成跟进资源”时显式调用；普通题目列表和答题不调用。 |
| Evidence/Citation | 历史答题记录有维度/知识点/得分；练习题没有题目来源、引用、题库 ID 或生成依据。 |
| 加载/空/失败 | `Promise.allSettled` 支持部分加载，错误提示；暂无专门的提交重试队列。 |
| 是否真实可用 | **混合实现（持久化答题 + Mock 演示题）**。答题会落库并触发确定性路径更新，但所做题不是后端任务实体。 |
| 主要问题 | 题库完全硬编码并在浏览器暴露正确答案；页面没有读取后端 `LearningTask`，也没有开始任务、截止时间、关联资源、正确率或可恢复任务状态。动态调整仅依据六维均分和最近两次同知识点错误，不含易混药、教师要求、每日学习时长和真实任务反馈。 |

### 3.4 学习报告

| 项目 | 当前实现 |
|---|---|
| 路由 | `/reports` |
| 页面文件 | `frontend/src/views/ReportsView.vue` |
| 主要组件 | 报告加载/生成、学习报告 Word 导出、最近识别任务 Word 导出、画像/路径/薄弱点摘要。 |
| 数据来源 | 后端 `ReportRecord`；学习报告服务明确创建 `title="Mock learning report"` 且 `data_source="mock"`。 |
| 调用接口 | `GET /reports/learning/{learner}`、`POST /reports/learning/{learner}/generate`、`POST /reports/learning/{learner}/export-word`、`POST /reports/tasks/{task}/export-word`、`GET /reports/{id}/download`。 |
| 是否使用 Agent | 否；后端报告由确定性服务和 Word 模板生成。 |
| 是否使用 RAG | 学习报告不调用；辨识报告从识别记录读取数据。 |
| Evidence/Citation | 学习报告 UI 不呈现证据、引用或报告生成 trace；识别报告也只按 `localStorage` 的最近任务 ID 导出。 |
| 加载/空/失败 | 有 loading、空态、生成/导出失败 toast；无生成任务异步状态或重试。 |
| 是否真实可用 | **Mock 演示 + 可真实下载文档**。Word 文件真实生成并受所有权校验，但核心学习分析不是实际统计报告。 |
| 主要问题 | 报告缺六维趋势、正确率、已完成任务数、高频错题、易混药、学习时长、资源完成率；没有 Agent 撰写摘要；当前内容是 profile/path/weak-points 快照。 |

### 3.5 证据链

| 项目 | 当前实现 |
|---|---|
| 路由 | `/traces` |
| 页面文件 | `frontend/src/views/TracesView.vue` |
| 主要组件 | Trace 列表、任务事件时间线、Agent 日志表、识别/检索/资源/路径摘要、完整 JSON 折叠区。 |
| 数据来源 | `TraceRecord`、`TaskEvent`、`AgentLog` 均有后端持久化模型；但默认 workflow/provider 为 mock。 |
| 调用接口 | `GET /traces`、选择记录后 `GET /agent/tasks/{id}/events` 与 `/logs`；同时读 `/metrics/overview` 和三项质量指标。 |
| 是否使用 Agent | 展示已有固定 LangGraph 任务的日志，不创建独立 Trace Agent。 |
| 是否使用 RAG | 仅读取 Trace 内已有 `knowledge_evidence/retrieval_id`；页面不再发起 RAG。 |
| Evidence/Citation | 可见证据数量和完整 trace JSON，但没有以可阅读清单展示每条 citation；也不显示 prompt 版本、完整模型调用输入/输出、是否重写、是否 replay/real/mock 的统一标识。 |
| 加载/空/失败 | 有 trace 空态、loading；事件/日志失败被静默吞掉，用户不会知道详情不完整。 |
| 是否真实可用 | **持久化 Trace 可用，业务内容默认 mock/固定流程**。 |
| 主要问题 | 学生端将系统任务成功率、知识来源和“幻觉/适配/覆盖”质量指标混入证据链；原始 JSON 可能暴露过多内部字段，虽当前日志做了摘要/脱敏，但缺专门的学生可见字段白名单。 |

### 3.6 测试指标

| 项目 | 当前实现 |
|---|---|
| 路由 | `/metrics` |
| 页面文件 | `frontend/src/views/MetricsView.vue` |
| 主要组件 | 学习者/药材/任务/资源/审核/来源计数、任务成功率、审核覆盖和通过率、质量指标、模型能力状态。 |
| 数据来源 | `/metrics/overview` 的计数来自数据库；`hallucination/adaptation/coverage` 均返回 `sample_count=0, metric_value=null, data_source=mock`；能力状态来自配置。 |
| 调用接口 | `GET /metrics/overview`、`GET /capabilities`、`GET /metrics/{hallucination|adaptation|coverage}`。 |
| 是否使用 Agent | 否。 |
| 是否使用 RAG | 否。 |
| Evidence/Citation | 不适用；只有知识来源总数。 |
| 加载/空/失败 | `Promise.allSettled` 支持部分加载；质量指标无样本时显示 `--`。 |
| 是否真实可用 | **混合页面**：计数/任务状态真实，质量指标是显式 mock。 |
| 主要问题 | 对学生展示大量系统质量和模型部署状态，混合了学生学习指标与运维指标；没有个人正确率、错题率、掌握率、难度适配、学习趋势、易混药等核心学习测量。 |

## 4. 当前真实数据流

下图只表达当前代码真实调用关系，而非目标架构。实线 `poll` 表示前端实际使用轮询；后端虽存在 SSE 路由，学生端未连接。

```mermaid
flowchart TD
  A[登录 / token] --> P[画像创建与初测]
  P -->|POST /tests/initial/submit| D[六维画像与弱项: DB]
  D -->|GET dimensions / weak-points| T[学习任务页]
  T --> Q[浏览器 questionBank 固定题]
  Q -->|POST /learning/answers| AH[答题历史: DB]
  AH -->|POST /learning-paths/update| LP[确定性规则学习路径: DB]
  LP --> R[学习资源页]
  R -->|POST /resources/generate| RG[资源服务: profile snapshot + 默认 mock/可选 real LLM]
  RG -->|POST /reviews/check| RV[规则审核 / 可选 real review]
  R --> RP[报告页]
  LP --> RP
  RP -->|POST /reports/learning/*| MR[Mock 学习报告 + Word]
  I[药材辨识上传] -->|POST /files/upload| F[文件记录]
  F -->|POST /agent/tasks| W[固定 LangGraph workflow]
  W --> V[Qwen / YOLO / mock 识别]
  W --> K[RAG 检索]
  W --> RG
  W --> LP
  W --> TR[Trace / TaskEvent / AgentLog: DB]
  I -->|GET task + events every 700ms| W
  W -.后端提供但前端未使用.-> SSE[/agent/tasks/{id}/stream]
  TR --> C[证据链页]
  K --> KN[药材知识页: 仅点击检索时]
```

闭环逐项结论：

| 步骤 | 前端页面 | 真实接口/数据模型 | 状态更新 | 结论 |
|---|---|---|---|---|
| 初始测试 | onboarding | `GET /tests/initial/questions`、`POST /tests/initial/submit` | 更新六维与诊断 | 已有真实接口。 |
| 六维画像 | onboarding/diagnosis/profile | `/profiles/*/dimensions` | DB | 已有。 |
| 识别薄弱点 | diagnosis | `/profiles/*/weak-points` | DB | 已有确定性诊断。 |
| 基于弱项资源生成 | resources/learning-tasks | `/resources/generate` | ResourceOutput DB | 资源保存有；resources 页不把弱项作为输入，任务页只选最低维度。 |
| 资源组织为任务 | 无相应任务列表实现 | 后端会创建 `LearningTask` | 任务推荐记录 DB | **学生端未读取/展示 `LearningTask`**。 |
| 做题/提交 | learning-tasks | `/learning/answers` | LearningAnswer DB | 已有，但题目是前端 Mock。 |
| 记录答题结果 | learning-tasks | 同上 | DB | 已有。 |
| 更新画像 | 无直接前端刷新维度的提交后动作 | 仅更新学习路径；初测会更新维度 | 路径版本 DB | **未证明常规答题更新六维画像/弱项**。 |
| 调整下一轮任务 | learning-tasks | `/learning-paths/update` | LearningPath + LearningTask DB | 确定性规则生成，前端未消费任务实体。 |
| 生成学习报告 | reports | `/reports/learning/*` | ReportRecord DB/Word | 有，但内容为 mock 快照。 |
| 保存全程 Trace | recognition/traces | `/agent/tasks` workflow → `/traces` | Trace/Event/Log DB | 仅识别固定工作流；学习任务答题与报告不进入同一 Trace。 |

因此，当前不存在完整的、真实的“学生画像→个性化任务→完成任务→更新画像→下一轮任务→统计报告→全程 Trace”前端闭环；存在两条部分闭环：初测/答题/确定性路径，以及辨识/固定工作流/Trace。

## 5. 当前 Agent 相关设计

前端的 Agent 概念集中在辨识页、证据链页和管理端的“智能体编排”。辨识页创建 `task_type=full_loop`，后端 `backend/app/workflows/graph.py` 固定串联：`load_profile → recognize_image → vision_review → retrieve_knowledge → judge_result → generate_resources → review_resources → update_learning_path → save_trace`。节点事件和 Agent 日志真实落库，Trace 页面读取它们；它不是纯 CSS 动画。

但实现仍有以下边界问题：

1. 后端路由对该流程的描述明确是 “fixed mock LangGraph workflow”；`execute_node()` 每个节点记录的输入摘要固定为 `mock node completed`，使日志的细粒度业务解释有限。
2. 前端实际使用 `setTimeout(..., 700)` 轮询 `/agent/tasks/{id}` 与 `/events`。后端提供了 `GET /agent/tasks/{id}/stream` SSE，但代码中没有 `EventSource`，故不具备真实 SSE 消费、断线恢复或增量事件处理。
3. 图片识别被强行作为 full-loop 的起点，并在同一任务中自动检索、生成资源、审核和更新路径。这与“识别为独立快速服务、可生成学习记录但不应依赖完整学习 Agent”的目标定位不一致。
4. 识别名由视觉融合服务决定，学习 Agent 没有直接决定药材名，这一点符合边界；但后续资源生成被固定触发，缺少由用户或学习计划选择的条件分支。

## 6. 当前 RAG 相关设计

RAG 在学生端有两类入口：

| 页面/场景 | 调用方式 | 是否阻塞 | 当前评价 |
|---|---|---|---|
| 药材知识 | 用户点击“检索证据”后 `POST /knowledge/retrieve` | 否 | 合理的按需使用，显示 citation/page/chunk。 |
| 学习任务跟进资源 | 先检索再生成资源 | 仅该按钮的同步流程 | 合理但生成完成前阻塞按钮；能传 retrieval/evidence id。 |
| 药材辨识 full-loop | workflow 固定 `retrieve_knowledge` 节点 | 是，工作流必经 | 不合理：图像识别被 RAG/资源生成/审核链路耦合。 |
| 学习资源页面手工生成 | 不调用检索 | 否 | 导致生成资源可能没有引用且 evidence snapshot 仍是 mock。 |
| 学习报告/指标/目录浏览 | 不调用 | 否 | 合理。 |

`HybridKnowledgeService` 会保存 retrieval/evidence 记录，检索响应包含 citation；默认 `rag_mode=mock`，MockRAGProvider 生成示例性“药典” citation，因此不能把它视为已接真实药典依据。页面也没有把 `provider/data_source/replay/fallback` 对资源的 citations 做完整展示。

## 7. 当前前后端接口对应表

| 页面 | 前端方法 | HTTP 接口 | 后端是否存在 | 字段是否匹配 |
|---|---|---|---|---|
| 画像/诊断 | `getProfile/getDimensions/getWeakPoints/diagnoseProfile` | `GET /profiles/{id}`、`/dimensions`、`/weak-points`；`POST /diagnose` | 是 | 匹配。 |
| 初测 | `getInitialQuestions/submitInitialTest` | `GET /tests/initial/questions`；`POST /tests/initial/submit` | 是 | 匹配。 |
| 药材知识 | `listMedicines/getMedicine/getMedicineFeatures/getSimilarMedicines` | `/medicines*` | 是 | 匹配。 |
| 知识证据 | `retrieveKnowledge` | `POST /knowledge/retrieve` | 是 | 匹配，返回 `retrieval_id/evidences`。 |
| 资源 | `listResources/getResource/generateResource/reviewResource` | `/resources*`、`/reviews/*` | 是 | 匹配；UI 未传 `retrieval_id/evidence_ids` 的常规路径。 |
| 学习任务 | `getLearningPath/listLearningAnswers/submitLearningAnswer/updateLearningPath` | `/learning-paths/*`、`/learning/answers/*` | 是 | 匹配；无获取 `LearningTask` 列表的前端方法。 |
| 报告 | `get/generate/export/download*Report` | `/reports/*` | 是 | 匹配；报告内容类型声明宽泛，未约束统计字段。 |
| 识别工作流 | `uploadFile/createTask/getTask/getTaskEvents/getTaskLogs` | `/files/upload`、`/agent/tasks*` | 是 | 基本匹配；后端 SSE `/stream` 无前端方法。 |
| Trace | `listTraces/getTracesByTask` | `/traces`、`/traces/by-task/{id}` | 是 | 匹配；后者当前学生端未使用。 |
| 指标/能力 | `getMetricsOverview/getQualityMetric/getCapabilities` | `/metrics/*`、`/capabilities` | 是 | 当前匹配：`CapabilityStatus` 已包含 `knowledge_catalog_loaded` 与 `knowledge_catalog_record_count`。审计过程中该契约曾短暂不一致，最终复验前已由并发改动补齐。 |
| 管理模型测试 | `testAdminModel` | `POST /admin/model-configs/{id}/test` | 是 | **潜在不匹配**：前端类型期待顶层 `reply`，后端实际为顶层 `result: {ok, reply}`；当前未见调用点。 |
| 管理通用 CRUD | `list/create/update/deleteAdminRecord` | `/admin/{resource}` | 是（白名单资源） | 匹配；仅允许 roles、menus、model-configs、agent-configs、prompt-templates、system-configs、test-cases。 |

## 8. 完整度矩阵

| 功能 | 已完成 | 接口已接 | Mock | 静态设计 | 缺失 |
|---|---:|---:|---:|---:|---:|
| 药材目录/详情/搜索 | 是 | 是 | 部分 RAG | 否 | 完整字段与分页交互不足。 |
| 按需证据检索 | 是 | 是 | 默认是 | 否 | 真实数据集配置/来源可信度待验证。 |
| 个性化资源列表/详情 | 是 | 是 | 默认内容是 | 否 | 画像驱动选择、citation 展示。 |
| 资源生成/审核 | 部分 | 是 | 默认是 | 否 | 异步工作流、人工审核入口、改写入口。 |
| 学习路径 | 是 | 是 | 确定性规则 | 否 | 前端未展示后端 LearningTask。 |
| 学习任务作答 | 部分 | 是 | 题库是 | 否 | 真任务、截止、资源关联、题目服务。 |
| 画像动态更新 | 初测有 | 部分 | 规则 | 否 | 常规答题到六维/弱项的闭环。 |
| 学习报告/导出 | 部分 | 是 | 学习内容是 | 否 | 真实统计、趋势、AI 解读。 |
| Trace/节点日志 | 是 | 是 | 默认工作流是 | 否 | 端到端覆盖、易读 citation、状态白名单。 |
| SSE | 后端有 | 否 | 否 | 否 | 前端消费与重连。 |
| 学生学习指标 | 少量 | 部分 | 质量项是 | 否 | 掌握率/错题率/趋势/易混药等。 |
| 系统质量指标 | 外观有 | 是 | 是 | 否 | 真实评测流水与分学生端展示。 |
| 管理 Agent/Prompt/模型 | CRUD | 是 | 测试项部分 | 否 | Agent 配置驱动工作流。 |
| RAG 数据集管理 | 后端有 | 否 | 可 mock | 否 | 管理端页面和学生影响链路。 |

## 9. 与目标架构的差异

### P0：阻塞真实业务

1. **学习任务不是服务端真实任务。** `LearningTasksView.vue` 将题目、正确答案和解释写在浏览器中，未读取后端 `LearningTask`；不能实现真实分配、截止、恢复、审计与安全判分。
2. **学习报告被明确标为 mock。** 后端 `generate_learning_report()` 写入 `Mock learning report` 和 `data_source=mock`，不能作为个性化学习业务报告。
3. **学习事件未形成统一闭环。** 初测、浏览器练习、资源生成、报告与辨识 workflow 分属不同数据路径；只有辨识任务保存全程 Trace，无法审计一次完整个性化学习周期。

### P1：业务定位错误/偏离

1. 识别页将快速识别与 RAG、资源生成、审核、路径更新强制编排为 full-loop；识别的成功与否被扩展为学习业务的完整条件。
2. 资源页主要是任意药材的手工生成器，并非基于学生画像和弱项的资源库；生成路径常无 retrieval/evidence 输入。
3. 任务动态性仅是“最低维度选一条固定题 + 最近两题规则更新路径”；未覆盖任务来源、资源关联、易混药、时间/教师条件。
4. 学生“测试指标”和 Trace 页面混入模型配置、任务成功率、幻觉率等系统运维内容；质量指标本身为 mock，不应作为学生学习成效展示。
5. 管理端 Agent 配置 CRUD 不被 `workflows/graph.py` 读取；PromptTemplate 仅资源生成服务读取第一个符合资源类型的启用模板，模型配置只在 resource generation/review 或手工测试中选择，不能控制固定 Agent 图。

### P2：体验与展示

1. Trace 页不直观展开 citation/evidence，且事件/日志加载失败被静默处理。
2. 资源详情遗漏学习目标、适用维度、生成原因、个性化标记、引用数、citation、prompt 版本和版本关系。
3. 报告页依赖 localStorage 的 `herbwise.last_task_id` 选择辨识报告，跨设备/清理浏览器后不可恢复。
4. 管理端保留大量 Soybean 模板路由及组件，容易造成菜单/权限/实际业务边界混淆。

## 10. 建议保留、修改和删除的内容

| 当前设计 | 保留/修改/删除 | 原因 |
|---|---|---|
| 药材目录与显式 RAG 检索分离 | 保留 | 浏览不阻塞 RAG，符合药材知识的正常查询边界。 |
| 画像、维度、弱项、答题历史的持久化接口 | 保留 | 已是个性化学习的可靠基础数据。 |
| 资源 profile/evidence/prompt 快照及审核记录 | 保留并前端展示 | 具备可追溯基础，但当前 UI 隐藏关键审计字段。 |
| 识别全量固定 workflow | 修改 | 将识别和学习编排拆开：识别完成后只产生识别/学习记录，由学习计划决定是否生成资源或任务。 |
| 浏览器 `questionBank` 与正确答案 | 删除/替换 | 必须改为服务端任务/题库和服务端判分。 |
| mock 学习报告 | 替换 | 保留 Word 导出服务，改用统计数据 + 可选 AI 摘要。 |
| 后端 SSE 与前端轮询 | 修改 | 使用 SSE 作为主通道，轮询作降级；保留现有事件持久化。 |
| 学生端系统指标/模型能力状态 | 移至管理端 | 学生端应展示个人学习指标；系统质量指标给管理员。 |
| Admin Agent/Prompt/Model 表单 | 保留并接入运行时 | 否则仅为配置壳；写入后必须被服务选择器和 Trace 消费。 |
| 管理端模板路由 | 删除或隔离 | 减少与业务路由、权限和演示组件的噪声。 |

## 11. 推荐页面职责

| 页面 | 应承担的职责 |
|---|---|
| 药材知识 | 权威目录、搜索筛选、完整结构化性状/风险信息、相似药对比；只有讲解、能力适配解释、引用查询、针对弱项练习才按需触发智能能力。 |
| 学习资源 | 展示已存在/已生成资源，清楚呈现知识点、难度、能力维度、生成来源、审核状态、引用、个性化原因和完成状态；生成应由画像/任务上下文驱动。 |
| 学习任务 | 读取服务端分配的任务，支持开始、作答、提交、截止、结果、关联资源与恢复；后端根据结果更新画像并调度下一轮。 |
| 学习报告 | 基于确定性统计展示六维、趋势、准确率、错题、易混药、时长与完成率；可选 Agent 只解释变化/生成摘要；由 ReportService 导出。 |
| 证据链 | 作为 Trace/审计查看器，呈现画像快照、知识卡/RAG evidence/citation、模型与 prompt 版本、事件耗时、审核/重写/降级及 data source；对学生做字段脱敏。 |
| 测试指标 | 学生端仅个人学习测量；系统 RAG/幻觉/模型耗时等质量指标在管理端独立呈现。 |

## 12. 建议的后续改造文件清单

| 文件 | 预计修改内容 | 优先级 |
|---|---|---|
| `frontend/src/types/api.ts` | 保持 Capability/报告/资源/Trace 契约与 OpenAPI 同步；收紧宽泛类型。 | P1 |
| `frontend/src/views/RecognitionView.vue` | 拆分识别与学习自动编排；接入 SSE + 降级轮询。 | P1 |
| `frontend/src/views/LearningTasksView.vue` | 删除硬编码题库和前端正确答案；改读真实任务、题目和关联资源。 | P0 |
| `frontend/src/services/api.ts` | 增加 learning tasks、题目、任务状态、SSE、资源 citation 等契约方法。 | P0 |
| `backend/app/modules/learning_paths/router.py` / `service.py` | 提供任务列表、开始、提交、统计、画像更新的接口；替换 mock 学习报告数据生产。 | P0 |
| `backend/app/modules/resources/business_service.py` | 让生成显式消费画像弱项/检索证据；正确记录真实/Mock provenance。 | P1 |
| `frontend/src/views/ResourcesView.vue` | 展示学习目标、维度、来源/审核/citation；从当前任务/弱项生成。 | P1 |
| `frontend/src/views/ReportsView.vue` | 展示真实统计趋势与报告生成状态；不依赖 localStorage 最近任务。 | P1 |
| `frontend/src/views/MetricsView.vue`、`TracesView.vue` | 从学生端移出系统指标，增加个人学习指标与可读证据清单。 | P1 |
| `backend/app/workflows/graph.py`、`nodes/main.py` | 将固定 full-loop 改为可配置、可选节点；丰富节点日志。 | P1 |
| `backend/app/modules/system/admin_router.py` | 将 Agent/SystemConfig 连接到运行时读取、版本化和生效验证。 | P1 |
| `admin-frontend/src/herbwise/*` | 增加资源、任务、画像、报告、Evidence/Trace、RAG Dataset、人工审核、错误管理的专用管理页。 | P1 |
| `admin-frontend/src/router/elegant/routes.ts` | 清理/隔离无关模板路由，形成业务权限矩阵。 | P2 |

## 13. 需要后端补充的接口

1. `GET /learning-tasks?learner_id&status`：返回真实分配任务，含 `task_id/title/type/source/resource_ids/dimensions/difficulty/deadline/status/progress/created_at`。
2. `GET /learning-tasks/{id}`、`POST /learning-tasks/{id}/start`、`POST /learning-tasks/{id}/answers`：题干不含答案；服务端判分，响应正确率、反馈、画像变化和下一步建议。
3. `GET /profiles/{learner_id}/learning-metrics`：返回个人六维趋势、正确率、错题率、高频错题、易混药、学习时长、资源完成率和难度适配，而非系统质量 KPI。
4. `GET /reports/learning/{learner_id}/statistics` 或将这些统计置入报告契约：使报告的确定性统计可审计；摘要字段单独标注 Agent/模型/prompt/data source。
5. `GET /resources/{id}/evidence` 或在资源详情返回 citation/evidence snapshot、target knowledge point、dimension、personalization reason、review provenance 和版本关系。
6. `GET /agent/tasks/{id}/stream` 的前端可消费认证方案（原生 EventSource 无法附加 Authorization header）及重放/游标协议；或提供安全 token query/Fetch SSE 方案。
7. 管理接口：资源/任务/画像/报告/Evidence/Trace/RAG dataset/人工审核/错误管理的分页查询与操作接口；AgentConfig/SystemConfig 的“当前生效版本、受影响节点、验证结果”接口。

## 14. 运行验证结果

| 项目 | 命令 | 结果 | 说明 |
|---|---|---|---|
| 学生端依赖 | `frontend/node_modules` 检查 | 通过 | 依赖目录存在。 |
| 学生端 typecheck | `npm.cmd run typecheck` | 通过 | 审计中途并发修改补齐了 `CapabilityStatus` 的知识目录字段；以最终工作区复验为准。 |
| 学生端 build | `npm.cmd run build` | 通过 | Vite 8.1.4，5219 modules transformed，19.29 秒完成。 |
| 学生端 lint | 未执行 | 无只读 lint 脚本 | `package.json` 未定义 lint；未引入/修改工具链。 |
| 管理端 typecheck | `pnpm.cmd run typecheck` | 通过（命令已进入下一步 build，未输出 type error） | `vue-tsc --noEmit --skipLibCheck` 完成后开始 Vite 构建。 |
| 管理端 build | `pnpm.cmd run build` | 超时 | 120 秒内未结束；输出停在 `vite build --mode prod`，没有可归因的源码错误。 |
| 管理端 lint | 未执行 | 该脚本为 `oxlint --fix && eslint --fix .`，会修改源码，违反本次“只审计、不改代码”。 |
| 后端相关测试 | `backend/.venv/Scripts/python.exe -m pytest tests/test_api_contracts.py tests/test_workflow_full.py -q` | 未启动 | 环境报 `uv trampoline failed to spawn Python child process: permission denied (os error 5)`；非代码断言失败。 |
| OpenAPI/接口检查 | 代码级路由对照 | 完成 | 已对照 FastAPI `api_router` 引入、核心 routers 和前端 API 方法；因 Python 运行环境权限问题未重新导出 OpenAPI。 |

运行验证不改变静态审计结论：接口大多存在且学生端当前可通过类型检查和生产构建，但个性化学习核心任务/报告仍处于 Mock 或规则演示状态。

## 终端摘要

1. 六个页面中没有一个可认定为“完整真实可用”的个性化学习闭环页面；药材知识的结构化浏览、资源/答题/Trace 的持久化接口可用，但均存在 Mock 或关键链路缺失。
2. 明确 Mock 或静态主导的页面至少 4 个：学习任务（题库静态）、学习报告（明确 mock）、测试指标（质量项 mock）、证据链（默认固定 mock workflow）；资源生成默认也为 mock，药材知识的 RAG 默认同样可为 mock。
3. 当前不存在真实完整的个性化学习闭环：答题可更新确定性路径，但未形成服务端任务→答题→画像更新→下一任务→真实统计报告的连续链路。
4. 当前 Agent 不是纯视觉包装：有固定 LangGraph、持久化事件/日志/Trace；但它是固定编排且默认 mock，Agent 配置页不能实际改变该图。
5. RAG 没有被放进药材目录的实时加载链路，这是合理的；但被固定嵌入图像识别 full-loop，造成不必要耦合。
6. 最严重的三项前端架构问题：学习任务题库/答案写死在浏览器、学习报告和质量指标仍为 Mock、学生页面混合运维指标并缺失真实任务/报告/Trace 闭环。
7. 报告路径：`docs/frontend-learning-agent-audit.md`。
