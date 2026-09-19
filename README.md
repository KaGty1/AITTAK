# AITTAK

## 项目简介

AITTAK 是一个红队 AI 中转站平台，部署在客户端与 AI API 上游之间，用于记录请求行为、通过监控用户 Prompt 及工具调用结果检测敏感信息泄露、以及通过在 SSE 注入工具调用实现任意命令执行。

## 核心能力

- **请求代理** — 支持 Claude（`/v1/messages`）和 OpenAI 兼容接口（`/v1/chat/completions`），流式和非流式均支持，透明重写 `model` 字段
- **行为监控** — 异步记录每次请求的 Prompt、工具调用、响应状态、耗时，支持按 Key/关键词/敏感类型筛选
- **敏感信息检测** — 内置 15 条 HaE 正则规则（手机号、身份证、JWT、AWS Key 等），支持自定义规则，实时扫描审计日志
- **工具注入** — 可配置规则，在模型调用特定工具时向 SSE 流注入额外的 `tool_use` 指令，客户端执行后结果被代理截获并记录，上游模型无感知
- **API Key 管理** — 代理签发独立的 `sk-proxy-*` Key，支持按 Key 追踪行为和定向注入
- **管理后台** — React SPA，管理上游配置、Key、审计日志、敏感规则、注入规则

## 架构

```text
客户端（Claude Code 等）
        │  sk-proxy-* Key
        ▼
┌─────────────────────────────┐
│  AITTAK (FastAPI)           │
│  ├─ /v1/*          数据面：透传 + 审计 + 注入剥离          │
│  ├─ /admin/api/*   控制面：管理 API                      │
│  └─ /               web/dist 静态托管（SPA）             │
└─────────────────────────────┘
        │  真实 API Key
        ▼
   上游 AI API
```

```text
.
├── app/
│   ├── main.py              # 装配：lifespan + 路由 + web/dist 托管
│   ├── proxy.py             # /v1/* 路由编排
│   ├── sse.py               # SSE 纯转换：model 重写、缓冲、注入事件
│   ├── upstream.py          # 上游解析、URL/Header 构建
│   ├── inject.py            # 注入规则匹配（纯）、事件生成（纯）、剥离（纯）、原子计数
│   ├── audit.py             # 提取（纯）+ 异步队列写入 + 注入结果日志
│   ├── sensitive.py         # 正则编译缓存 + 扫描（纯）
│   ├── auth.py              # API Key 验证 + 管理员验证（constant-time）
│   ├── database.py          # SQLite Schema、迁移、种子规则
│   └── api/                 # 管理面按资源拆分 + 通用 CRUD
├── web/                     # 前端工程（React 18 + TS + Vite + Tailwind）
│   └── src/
│       ├── lib/             # api / types / hooks(usePoll) / utils
│       ├── components/ui/   # Button/Field/Modal/ConfirmDialog/DataTable/Tag/…
│       ├── components/      # 领域组件（monitor/keys/inject/settings/upstreams）
│       └── pages/           # Monitor / Upstreams / Keys / Inject / Settings
├── tests/                   # pytest：SSE 转换、注入剥离、敏感扫描、CRUD
└── requirements.txt
```

## 快速开始

### 环境要求

- Python 3.11+
- Node 18+（构建前端）

### 安装

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
cp .env.example .env
```

### 运行

```bash
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问管理后台：`http://localhost:8000/`（旧入口 `/admin` 自动重定向）

默认管理员密码：`changeme`（通过 `ADMIN_PASSWORD` 环境变量修改）

### 前端开发模式

```bash
cd web && npm run dev        # http://localhost:5173，/admin/api 代理到本地后端
```

### 测试

```bash
.venv/bin/pytest             # 后端：31 个用例
cd web && npm test           # 前端：交互冒烟测试
```

### 配置客户端

以 Claude Code 为例，将 API 地址指向代理：

```bash
export ANTHROPIC_BASE_URL=http://your-proxy-host:8000
export ANTHROPIC_API_KEY=sk-proxy-xxxxxxxx
```

## 配置项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `PORT` | `8000` | 服务监听端口 |
| `ADMIN_PASSWORD` | `changeme` | 管理后台登录密码 |
| `DB_PATH` | `data/audit.db` | SQLite 数据库文件路径 |
| `LOG_RETENTION_DAYS` | `90` | 审计日志保留天数 |
| `MAX_BODY_SIZE` | `102400` | 工具调用内容截断阈值（字节） |

## 使用说明

### 上游配置

管理后台「上游配置」中添加 AI API 提供商：平台（claude / openai）、Base URL、上游真实 API Key。代理按请求路径自动路由到对应平台的上游。

### 工具注入

在模型调用工具时额外注入一条工具调用指令，客户端执行后结果被代理截获（不发给上游），仅记录在审计日志：

- **触发工具**：模型调用哪些工具时触发（留空 = 任意工具）
- **注入工具**：Read / Bash / Glob / Grep / Write / Edit
- **注入参数**：JSON 格式的工具入参（表单按工具提供模板）
- **目标 Key**：仅对特定 API Key 生效（留空 = 全部）
- **最大触发次数**：达到上限后停止注入（原子计数，并发安全）

## 安全说明

- 前端产物零外网依赖（字体自托管），支持内网/离线部署
- 管理面静态文件托管带路径穿越防护
- 管理员密码比对使用 constant-time 比较
- 本工具仅限授权红蓝对抗与内部安全评估使用
