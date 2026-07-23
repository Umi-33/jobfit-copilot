# JobFit Copilot

JobFit Copilot 是一个求职岗位分析与面试准备 MVP。用户输入脱敏后的候选人画像和岗位 JD，规则引擎负责解析、评分、风险识别和行动建议；用户保存分析记录并明确授权后，后端可调用 GroqCloud 生成结构化面试准备内容。LLM 不参与岗位评分，也不会自动投递。

## 技术栈

- Vue 3、Vue Router、Vite
- FastAPI、Pydantic、SQLite
- GroqCloud（通过 OpenAI 兼容 API 调用）

## 本地运行

安装后端依赖并从仓库根目录启动：

```bash
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

启动前端开发服务器：

```bash
cd frontend
npm ci
npm run dev
```

Vite 开发服务器会将相对 `/api` 请求代理到 `http://127.0.0.1:8000`。

## 环境变量

后端环境变量：

- `GROQ_API_KEY`：GroqCloud API Key；只配置在后端。
- `GROQ_MODEL`：面试准备使用的 Groq 模型。
- `GROQ_TIMEOUT_SECONDS`：可选，请求超时秒数，默认 30。
- `FRONTEND_ORIGINS`：逗号分隔的公开前端 Origin。后端默认额外允许本地 5173 端口。
- `JOBFIT_DATABASE_PATH`：可选 SQLite 路径。
- `DEMO_ACCESS_CODE`：可选演示访问码；为空时不启用保护。

前端构建变量见 `frontend/.env.example`：

- `VITE_API_BASE_URL`：公开后端 Origin，不包含末尾 `/api`。
- `VITE_DEMO_ACCESS_REQUIRED`：设为 `true` 时显示演示码入口。

不要在任何 `VITE_` 变量中放置 Groq Key。后端不会自动读取本地 `.env`，本地运行时请通过 shell 注入；Vite 会从 `frontend` 目录读取前端环境文件。部署时通过对应平台的 Secret/环境变量配置。

## FastAPI Cloud 后端

- GitHub 仓库：`Umi-33/jobfit-copilot`
- Application / Root Directory：留空，使用仓库根目录
- Python：3.11 系列
- FastAPI 入口：`backend.app.main:app`
- Health Check Path：`/api/health`

在 FastAPI Cloud Dashboard 配置以下后端环境变量：

- `GROQ_API_KEY`：必需，标记为 Secret。
- `GROQ_MODEL`：必需，配置面试准备使用的模型。
- `GROQ_TIMEOUT_SECONDS`：可选，请求超时秒数。
- `DEMO_ACCESS_CODE`：受控演示启用时配置，并标记为 Secret。
- `JOBFIT_DATABASE_PATH`：可选 SQLite 写入路径，需以平台实际支持的可写路径为准。
- `FRONTEND_ORIGINS`：Vercel 正式 Origin，不包含末尾斜杠；多个 Origin 使用逗号分隔。

不要将 Key、演示码或其他真实环境变量值提交到仓库。

## Vercel 前端

- Root Directory：`frontend`
- Install Command：`npm ci`
- Build Command：`npm run build`
- Output Directory：`dist`

设置 `VITE_API_BASE_URL` 为 FastAPI Cloud 公开后端地址，不包含末尾 `/api`。同时将该 Vercel 正式域名写入后端 `FRONTEND_ORIGINS`，且不包含末尾斜杠。若后端启用了 `DEMO_ACCESS_CODE`，同时设置 `VITE_DEMO_ACCESS_REQUIRED=true`。`frontend/vercel.json` 为 Vue History 路由提供回退，并为页面添加 `noindex, nofollow` 响应头。

## Demo 数据与能力边界

公开 Demo 使用临时共享 SQLite。FastAPI Cloud 本地文件不保证持久化，记录可能因实例变化或重新部署而丢失；所有获授权访客共享同一套可见数据，也不具备用户级数据隔离。请勿输入真实姓名、联系方式、未公开简历、公司内部信息或其他敏感数据，只使用脱敏或虚构内容。

授权生成面试准备后，当前记录中的候选人画像、岗位 JD、规则分析和行动计划会发送给外部大模型服务。生成结果只保留在当前页面，不写入 SQLite，刷新后会消失。

演示码只是公开 Demo 的轻量访问限制，不是正式账号、用户认证、权限管理或数据隔离系统。本项目目前不包含自动投递、用户数据隔离、生产级 RAG 或复杂自主 Agent。
