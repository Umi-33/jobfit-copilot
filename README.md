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

## Render 后端

- Root Directory：仓库根目录
- Build Command：`pip install -r requirements.txt`
- Start Command：`python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path：`/api/health`
- 建议临时 Demo 设置：`JOBFIT_DATABASE_PATH=/tmp/jobfit_copilot.sqlite3`

在 Render 配置 Groq 变量、正式前端 `FRONTEND_ORIGINS`，并在需要受控演示时配置 `DEMO_ACCESS_CODE`。不要将这些值提交到仓库。

## Vercel 前端

- Root Directory：`frontend`
- Install Command：`npm ci`
- Build Command：`npm run build`
- Output Directory：`dist`

设置 `VITE_API_BASE_URL` 为 Render 后端公开 Origin。若后端启用了 `DEMO_ACCESS_CODE`，同时设置 `VITE_DEMO_ACCESS_REQUIRED=true`。`frontend/vercel.json` 为 Vue History 路由提供回退，并为页面添加 `noindex, nofollow` 响应头。

## Demo 数据与能力边界

公开 Demo 使用临时共享 SQLite。记录可能被其他获授权访客看到，也可能在服务休眠、重启或重新部署后丢失。请勿输入真实姓名、联系方式、未公开简历、公司内部信息或其他敏感数据，只使用脱敏或虚构内容。

授权生成面试准备后，当前记录中的候选人画像、岗位 JD、规则分析和行动计划会发送给外部大模型服务。生成结果只保留在当前页面，不写入 SQLite，刷新后会消失。

演示码只是公开 Demo 的轻量访问限制，不是正式账号、用户认证、权限管理或数据隔离系统。本项目目前不包含自动投递、用户数据隔离、生产级 RAG 或复杂自主 Agent。
