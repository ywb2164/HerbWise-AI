# 本草智策 HerbWise AI

## V0.3A backend status

The V0.3A branch builds on the V0.2 database-backed
JWT/RBAC, learner profiles and initial assessment, structured demonstration
medicine knowledge, persisted mock resources/reviews, versioned learning paths,
traces, metrics, OpenAPI export, and frontend mock contracts.

V0.3A retains Mock defaults while adding OpenAI-compatible real LLM/Qwen-VL
adapters, a lazy local Ultralytics adapter, database name normalization, and
deterministic hybrid fusion. Supported vision modes are `mock`, `qwen`,
`local`, and `hybrid`; LLM modes are `mock` and `real`; `RAG_MODE` remains
`mock`. Demo accounts created by `backend/scripts/seed_data.py` are
`admin` / `HerbWise@2026` and `student` / `HerbWise@2026`.

Run migrations and seed twice in Docker before exercising the smoke script:

```powershell
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run python scripts/seed_data.py
docker compose exec api uv run python scripts/seed_data.py
docker compose exec api uv run python scripts/smoke_v02.py
docker compose exec api uv run python scripts/smoke_v03a_fake.py
```

Swagger is available at `http://localhost:8000/docs`; exported API contract is
`docs/openapi.json`. V0.3 should introduce real providers in this order:
OpenAI-compatible client, Qwen-VL, structured name matching, RAGFlow, resource
generation/review, then YOLO or ONNX inference.

> 中药智能鉴别与临床药事质控实训个性化知识生成与多智能体协同决策系统

本项目面向中药饮片鉴别、临床药事质控、院校实训教学与药企质检培训场景，计划构建“学习者画像 → 图像识别 → 视觉复核 → 药典知识检索 → 纠错裁判 → 个性化资源生成 → 内容审核 → 学习路径更新 → 证据链归档”的完整闭环。

当前仓库处于 **V0.1 后端骨架阶段**：已完成 FastAPI、MySQL、Redis、Alembic、LangGraph 与 Mock Provider 的基础集成，并已成功跑通一次完整 Mock 工作流。

---

## 1. 当前进度

### 已完成

- Windows 11 + WSL2 + Docker Desktop 开发环境。
- Python 3.12 + `uv` 项目依赖管理。
- FastAPI 单体分模块后端骨架。
- SQLAlchemy 2.x 异步数据库访问。
- MySQL 8.4 与 Redis 7.2 Docker 容器。
- Alembic 数据库迁移。
- 统一配置、响应、异常、日志和 `request_id` 中间件。
- 基础任务数据表与证据链数据表。
- Provider 抽象层与 Mock 实现。
- LangGraph 固定 DAG 工作流。
- 任务创建、状态查询、事件查询和 Agent 日志接口骨架。
- Mock 工作流成功完成并写入 MySQL。
- 中文 UTF-8 返回问题已修复。
- Ruff 检查通过。
- mypy 类型检查通过。
- Git 仓库已创建并上传当前代码。

### 已跑通的 Mock 闭环

```text
load_profile
    ↓
recognize_image
    ↓
vision_review
    ↓
retrieve_knowledge
    ↓
judge_result
    ↓
generate_resources
    ↓
review_resources
    ↓
update_learning_path
    ↓
save_trace
```

成功任务示例：

```json
{
  "status": "success",
  "current_node": "save_trace",
  "progress": 100,
  "retry_count": 0,
  "errors": []
}
```

### 尚未完成

- 完整用户认证、JWT、刷新令牌与 RBAC。
- 学生、教师、临床药师、药企质检人员、管理员五角色权限。
- 学习者画像完整 CRUD、诊断与动态更新规则。
- 药材结构化知识库与别名字典。
- 真实 Qwen / Qwen-VL / DeepSeek 接入。
- 真实 YOLO 或 ONNX Runtime 推理。
- RAGFlow 知识库接入。
- New API / one-api 模型网关接入。
- 在线资源生成、审核纠偏与报告导出。
- 完整 SSE 前端联调与断线恢复验收。
- 文件上传接口完整验收。
- RAGAS / DeepEval 离线评测。
- 生产级异步任务队列、失败恢复和限流。

---

## 2. 当前技术栈

### 后端

- FastAPI
- Python 3.12
- uv
- SQLAlchemy 2.x Async
- Alembic
- Pydantic Settings
- LangGraph
- Redis Async Client
- OpenAI Python SDK（预留）
- Structlog / ORJSON
- Pytest / Ruff / mypy

### 基础设施

- Docker Desktop
- Docker Compose
- MySQL 8.4
- Redis 7.2 Alpine

### 后续计划接入

- Qwen-VL：视觉识别与复核
- Qwen / DeepSeek：资源生成与审核
- RAGFlow：药典、教材与质控资料检索
- YOLO / ONNX Runtime：本地识别与备用推理
- New API / one-api：多模型统一网关
- ECharts / Vue Flow：画像与智能体流程可视化

---

## 3. 当前系统架构

```text
┌─────────────────────────────────────────┐
│               Vue3 前端（待接入）       │
└───────────────────┬─────────────────────┘
                    │ REST / SSE
┌───────────────────▼─────────────────────┐
│              FastAPI 后端               │
│                                         │
│ 任务管理 │ 画像 │ 识别 │ RAG │ 资源 │ 审核 │
│ 路径规划 │ 证据链 │ 指标 │ 文件管理      │
│                                         │
│         LangGraph 固定 DAG              │
└──────────────┬──────────────┬───────────┘
               │              │
        ┌──────▼──────┐ ┌────▼─────┐
        │ MySQL 8.4   │ │ Redis 7.2│
        └─────────────┘ └──────────┘

当前：Mock Provider
后续：Qwen-VL / Qwen / DeepSeek / RAGFlow / YOLO
```

---

## 4. 项目目录

```text
HerbWise-AI/
├─ backend/
│  ├─ app/
│  │  ├─ api/                 # 总路由
│  │  ├─ core/                # 配置、数据库、Redis、日志、异常、中间件
│  │  ├─ common/              # 公共枚举、Schema、ID 工具
│  │  ├─ modules/             # 业务模块
│  │  ├─ integrations/        # LLM、Vision、RAG、Storage Provider
│  │  ├─ workflows/           # LangGraph 状态、节点和执行器
│  │  └─ main.py
│  ├─ migrations/             # Alembic 迁移
│  ├─ scripts/                # 初始化与种子数据脚本
│  ├─ tests/
│  ├─ pyproject.toml
│  ├─ uv.lock
│  ├─ Dockerfile
│  ├─ .dockerignore
│  └─ .env.example
├─ data/
│  ├─ uploads/
│  ├─ reports/
│  ├─ models/
│  └─ knowledge/
├─ docs/
├─ compose.yaml
└─ README.md
```

> 实际目录以仓库当前代码为准；后续新增模块应保持 `router / schemas / service / repository / models` 的统一结构。

---

## 5. 环境要求

- Windows 11
- WSL2
- Docker Desktop
- Docker Compose
- Git
- uv
- Python 3.12（宿主机调试时使用）

检查环境：

```powershell
docker --version
docker compose version
uv --version
git --version
```

---

## 6. 快速启动

### 6.1 克隆仓库

```powershell
git clone <仓库地址>
Set-Location HerbWise-AI
```

### 6.2 创建本地环境变量

```powershell
Copy-Item backend\.env.example backend\.env
```

开发模式默认建议：

```env
AI_MODE=mock
RAG_MODE=mock
YOLO_MODE=mock
```

不要将真实 `.env`、API Key、模型权重或药典全文提交到 Git。

### 6.3 启动容器

```powershell
docker compose config
docker compose up -d --build
docker compose ps
```

当前服务端口：

| 服务 | 宿主机地址 |
|---|---|
| FastAPI | `http://localhost:8000` |
| Swagger | `http://localhost:8000/docs` |
| MySQL | `localhost:3307` |
| Redis | `localhost:6380` |

### 6.4 执行数据库迁移

```powershell
docker compose exec api uv run alembic upgrade head
```

### 6.5 写入示例数据

```powershell
docker compose exec api uv run python scripts/seed_data.py
```

### 6.6 验证服务

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ready
```

---

## 7. 当前基础接口

### 系统接口

```text
GET /
GET /health
GET /ready
```

### Agent 任务

```text
POST /api/agent/tasks
GET  /api/agent/tasks/{task_id}
GET  /api/agent/tasks/{task_id}/events
GET  /api/agent/tasks/{task_id}/logs
GET  /api/agent/tasks/{task_id}/stream
```

### 文件接口

```text
POST /api/files/upload
GET  /api/files/{file_id}
```

接口详情以 Swagger 为准：

```text
http://localhost:8000/docs
```

---

## 8. 创建并查询 Mock 任务

### 创建任务

```powershell
$response = Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/agent/tasks" `
  -ContentType "application/json" `
  -Body '{"learner_id":"stu_001","task_type":"full_loop","image_id":"img_mock_001"}'

$response | ConvertTo-Json -Depth 20
```

### 获取任务 ID

```powershell
$taskId = $response.data.task_id
if (-not $taskId) {
    $taskId = $response.task_id
}
$taskId
```

### 查询任务

```powershell
Start-Sleep -Seconds 3

Invoke-RestMethod `
  -Method Get `
  -Uri "http://localhost:8000/api/agent/tasks/$taskId" |
  ConvertTo-Json -Depth 20
```

### 查询事件

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://localhost:8000/api/agent/tasks/$taskId/events" |
  ConvertTo-Json -Depth 20
```

### 查询 Agent 日志

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://localhost:8000/api/agent/tasks/$taskId/logs" |
  ConvertTo-Json -Depth 20
```

---

## 9. 当前数据库表

V0.1 阶段至少包含：

```text
alembic_version
agent_logs
learner_dimensions
learner_profiles
task_events
task_records
trace_records
uploaded_files
```

查看数据库表：

```powershell
docker compose exec db `
  mysql -uherbwise -pherbwise herbwise `
  -e "SHOW TABLES;"
```

数据库结构变化必须通过 Alembic 迁移完成，不应依赖手工建表。

---

## 10. 代码质量检查

```powershell
docker compose exec api uv run pytest
docker compose exec api uv run ruff format --check .
docker compose exec api uv run ruff check .
docker compose exec api uv run mypy app
```

当前已确认：

```text
Ruff：通过
mypy：通过
```

Pytest 结果应以当前分支实际执行结果为准。

---

## 11. 常用 Docker 命令

### 启动

```powershell
docker compose up -d
```

### 重新构建 API

```powershell
docker compose up -d --build api
```

### 查看状态

```powershell
docker compose ps
```

### 查看 API 日志

```powershell
docker compose logs -f api
```

### 停止服务

```powershell
docker compose down
```

> 不要随意执行 `docker compose down -v`，该命令会删除 MySQL 与 Redis 数据卷。

---

## 12. 开发约定

### 分支建议

```text
main        稳定版本
develop     日常集成
feature/*   功能开发
fix/*       缺陷修复
release/*   候选发布
```

### 模块原则

- 不把业务代码堆入 `main.py`。
- Router 只处理 HTTP 请求与响应。
- Service 负责业务逻辑。
- Repository 负责数据库访问。
- Pydantic Schema 与 SQLAlchemy Model 分离。
- AI、视觉和 RAG 必须通过 Provider 抽象调用。
- 数据库迁移只新增 Alembic revision，不修改已经使用的历史迁移。
- 所有新增接口必须包含类型注解、错误处理和测试。

### 敏感文件

以下内容禁止提交：

```text
backend/.env
API Key
.venv/
*.pt
*.pth
*.onnx
真实上传文件
数据库数据卷
药典全文
生成报告
```

---

## 13. 下一阶段计划

### V0.2：完整业务后端框架

- JWT 与 RBAC。
- 多角色菜单权限。
- 学习者画像、薄弱点与历史记录。
- 药材、别名、性状、切面和相似药材结构化数据。
- 资源生成与审核数据表。
- 学习路径、答题与报告模块。
- 后台模型、Agent、Prompt 与测试用例配置。
- 证据链和指标接口完善。

### V0.3：真实 AI 能力接入

建议顺序：

```text
OpenAI 兼容模型客户端
→ Qwen-VL 视觉识别
→ 药材标准名与别名匹配
→ RAGFlow 检索
→ 真实资源生成
→ 第二模型审核
→ YOLO / ONNX Runtime
→ 离线评测
```

### V1.0：比赛演示版本

- Vue3 页面联调。
- Agent 流程图和 SSE 实时状态。
- 学习者画像雷达图。
- 多模态识别页面。
- 个性化讲义、指南和分阶测试题。
- 内容审核纠偏。
- 学习路径与报告。
- 证据链与指标大屏。
- 真实模式 / Mock 模式 / 回放模式。

---

## 14. 当前技术债

- 当前后台任务执行器适合开发验证，不是生产级可靠队列。
- Provider 仍为 Mock 实现。
- LangGraph 状态结构和业务表还需随 V0.2 继续固化。
- MySQL、Redis 当前端口暴露用于本地开发，生产部署需收紧网络。
- SSE 需要继续验证断线、重连与历史事件补发。
- 文件上传需要继续完成边界测试、权限和清理策略。
- 指标与幻觉率必须使用明确测试口径，不能直接使用 Mock 数据作为真实结论。

---

## 15. 项目状态

```text
当前版本：V0.1 Backend Skeleton
运行模式：Mock
主流程状态：已跑通
数据库迁移：已启用
Docker：FastAPI + MySQL + Redis 正常运行
真实模型：未接入
前端：待联调
```

---

## 16. 许可证

当前仓库用于比赛开发与团队协作，正式开源许可证尚未确定。后续公开发布前，应统一审查第三方依赖、模型权重、药典数据与训练数据的许可证和版权要求。
