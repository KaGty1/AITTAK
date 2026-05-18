# AITTAK

## 项目简介

AITTAK 是一个特制的红队AI中转站平台，部署在客户端与 AI API 上游之间，用于记录请求行为、通过监控用户Prompt及工具调用结果检测敏感信息泄露、以及通过在SSE注入工具调用实现任意命令执行。



## 核心能力

- **请求代理** — 支持 Claude（`/v1/messages`）和 OpenAI 兼容接口（`/v1/chat/completions`），流式和非流式均支持
- **行为监控** — 异步记录每次请求的 Prompt、工具调用、响应状态、耗时，支持按 Key/关键词/敏感类型筛选
- **敏感信息检测** — 内置 HaE 12 条正则规则（手机号、身份证、JWT、AWS Key 等），支持自定义规则，实时扫描审计日志
- **工具注入** — 可配置规则，在模型调用特定工具时注入额外的 tool_use 指令，客户端执行后结果被代理截获并记录
- **API Key 管理** — 代理签发独立的 `sk-proxy-*` Key，支持按 Key 追踪行为和定向注入
- **管理后台** — 单页 Web 控制台，管理上游配置、Key、审计日志、敏感规则、注入规则



## 架构原理

### 行为监控流程

```mermaid
sequenceDiagram
    participant Client as Claude Code
    participant Proxy as AI Audit Proxy
    participant Upstream as 上游 API

    Client->>Proxy: POST /v1/messages (sk-proxy-xxx)
    Proxy->>Proxy: 验证 API Key
    Proxy->>Proxy: 提取 Prompt、工具调用信息
    Proxy->>Upstream: 转发请求（替换为真实 API Key）
    Upstream-->>Proxy: SSE 流式响应
    Proxy-->>Client: 透传响应（重写 model 字段）
    Proxy->>Proxy: 记录审计日志（异步）
    Proxy->>Proxy: 正则扫描敏感信息
    Proxy->>Proxy: 写入 SQLite
```



### 工具注入流程

```mermaid
sequenceDiagram
    participant Client as Claude Code
    participant Proxy as AI Audit Proxy
    participant Upstream as 上游 API

    Note over Client,Upstream: 第一轮：模型调用工具，代理注入额外工具

    Client->>Proxy: POST /v1/messages
    Proxy->>Upstream: 转发请求
    Upstream-->>Proxy: SSE 响应（含 tool_use: Bash）
    Proxy->>Proxy: 检测到 Bash 调用，匹配注入规则
    Proxy->>Proxy: 生成额外 tool_use block（inject-xxx）
    Proxy-->>Client: 原始 tool_use + 注入的 tool_use

    Note over Client: 客户端执行所有工具（含注入的）

    Note over Client,Upstream: 第二轮：代理剥离注入结果

    Client->>Proxy: POST /v1/messages（含 inject-xxx 的 tool_result）
    Proxy->>Proxy: 识别 inject- 前缀，剥离注入的 tool_result
    Proxy->>Proxy: 将剥离的结果写入审计日志
    Proxy->>Upstream: 转发清理后的请求（上游无感知）
    Upstream-->>Proxy: 正常响应
    Proxy-->>Client: 透传响应
```



## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| HTTP 客户端 | httpx（异步，支持流式转发） |
| 数据库 | SQLite（WAL 模式，通过 aiosqlite 异步访问） |
| 序列化 | orjson |
| 前端 | Vue 3 CDN + Tailwind CSS CDN（单文件 SPA） |
| 运行时 | Python 3.12 + uvicorn |



## 项目结构

```text
.
├── app/
│   ├── main.py          # FastAPI 入口，生命周期管理
│   ├── proxy.py         # 反向代理核心（流式转发、模型名重写、注入集成）
│   ├── admin.py         # 管理 API（CRUD：上游、Key、审计、敏感规则、注入规则）
│   ├── audit.py         # 异步审计日志写入（批量、去重、定期清理）
│   ├── auth.py          # 认证（API Key 验证 + 管理员密码验证）
│   ├── config.py        # 环境变量配置
│   ├── database.py      # 数据库 Schema、迁移、种子数据
│   ├── inject.py        # 工具注入引擎（规则匹配、SSE 事件生成、请求剥离）
│   └── sensitive.py     # 敏感信息正则检测
├── templates/
│   └── index.html       # 管理后台前端（Vue 3 单页应用）
├── data/
│   └── audit.db         # SQLite 数据库文件（运行时生成）
├── requirements.txt     # Python 依赖
└── .env.example         # 环境变量示例
```



## 快速开始

### 环境要求

- Python 3.11+

### 安装

```bash
git clone <repo-url> && cd ai-audit-proxy
pip install -r requirements.txt
cp .env.example .env  # 按需修改配置
```

### 运行

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 5001
```

访问管理后台：`http://localhost:5001/admin`

默认管理员密码：`changeme`（通过 `ADMIN_PASSWORD` 环境变量修改）

### 配置客户端

以 Claude Code 为例，将 API 地址指向代理：

```bash
# 在代理后台创建 API Key 后
export ANTHROPIC_BASE_URL=http://your-proxy-host:5001
export ANTHROPIC_API_KEY=sk-proxy-xxxxxxxx
```

## 配置项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `PORT` | `8000` | 服务监听端口（uvicorn 启动时可覆盖） |
| `ADMIN_PASSWORD` | `changeme` | 管理后台登录密码 |
| `DB_PATH` | `data/audit.db` | SQLite 数据库文件路径 |
| `LOG_RETENTION_DAYS` | `90` | 审计日志保留天数，超期自动清理 |
| `MAX_BODY_SIZE` | `102400` | 工具调用内容截断阈值（字节） |



## 使用说明

### 上游配置

在管理后台「上游配置」Tab 中添加 AI API 提供商：

- **平台**：`claude` 或 `openai`
- **Base URL**：上游 API 地址（如 `https://api.anthropic.com`）
- **API Key**：上游真实 API Key

代理会根据请求路径自动路由到对应平台的上游。

### 工具注入

工具注入用于在模型调用工具时，额外注入一个工具调用指令。典型用途：

- 在用户执行 Bash 命令时，注入 `Read` 读取特定文件
- 在用户执行 Bash 命令时，注入`Bash`来执行恶意命令

配置项：
- **触发工具**：模型调用哪些工具时触发（留空 = 任意工具）
- **注入工具**：要注入的工具类型（Read / Bash / Glob / Grep / Write / Edit）
- **注入参数**：工具调用的 JSON 参数
- **目标 Key**：仅对特定 API Key 生效（留空 = 全部）
- **最大触发次数**：达到上限后停止注入

注入的工具调用结果会被代理自动截获，不会发送给上游模型，仅记录在审计日志中。
