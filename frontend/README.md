# HerbWise-AI Frontend

本草智策前端使用 Vue 3、TypeScript 和 Vite，组件库为 Naive UI。前端直接对接仓库中的 FastAPI 后端，支持登录、药材辨识智能体、学情画像、知识证据、学习资源、Word 报告和 Trace 追踪。

## 本地运行

先启动根目录中的 Docker 后端，确保 `http://localhost:8000/health` 可访问。

```powershell
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。Vite 会将 `/api` 代理到 `http://localhost:8000`，开发环境不需要额外的 CORS 配置。

演示账号：

- 学生：`student / HerbWise@2026`
- 管理员：`admin / HerbWise@2026`
- 默认学习者：`stu_001`

首次联调建议使用 `mock` 视觉模式，不依赖外部模型密钥或 RAGFlow。

## 常用命令

```powershell
npm run typecheck
npm run build
npm run preview
```

## 页面路由

| 路由 | 页面 |
|---|---|
| `/login` | 登录 |
| `/dashboard` | 工作台 |
| `/recognition` | 药材辨识与九节点智能体任务 |
| `/profile` | 六维学情画像与学习路径 |
| `/knowledge` | 药材档案与知识证据检索 |
| `/resources` | 个性化学习资源与审核 |
| `/reports` | 学习报告与 Word 导出 |
| `/traces` | Trace、Agent 日志与质量指标 |

API 层同时兼容 `{ code, message, data, request_id }` 包装响应和上传、任务端点的直接响应。访问令牌过期时会尝试刷新，刷新失败则返回登录页。
