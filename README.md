# Laiver 用户部署与使用教程

Laiver 是一个面向个人长期陪伴场景的 personalized AI companion / personal agent 原型。它不是单纯的聊天页面，而是把聊天记录导入、Persona 生成、长期记忆、模型接入、Skill、连接器和本地微调串成一条可本地运行的工作流。

当前项目处于 **MVP+ / early alpha** 阶段：核心链路已经可以本地跑通，适合个人试用、功能验证和继续产品化打磨；暂不建议当作生产系统对外部署。

## 你会得到什么

启动后，你可以在浏览器里完成这条主流程：

```text
上传聊天记录 -> 预览并保存 -> 选择目标 speaker -> 生成 Persona
-> 配置模型与 Skill -> 进入 Chat 测试 -> 查看长期记忆与调试信息
```

主要页面：

- 首页控制台：<http://localhost:3000>
- 首次使用向导：<http://localhost:3000/onboarding>
- 聊天记录导入：<http://localhost:3000/imports>
- Persona 管理：<http://localhost:3000/persona>
- Chat 测试：<http://localhost:3000/chat>
- Memory 调试：<http://localhost:3000/memories>
- 模型设置：<http://localhost:3000/settings>
- Skill 管理：<http://localhost:3000/skills>
- Connector 管理：<http://localhost:3000/connectors>
- 训练任务：<http://localhost:3000/training>
- API 文档：<http://localhost:8000/docs>

## 部署方式选择

Laiver 支持两种本地运行方式。

### 方式 A：轻量本地模式

适合第一次试用。后端使用 SQLite，本地不需要 PostgreSQL / Redis / Qdrant，也不需要 Docker 正常运行。

这种模式能体验主要页面、导入、Persona、Chat、Memory 基础链路和模型 fallback；但不等同于完整基础设施部署。

### 方式 B：Docker 完整模式

适合更接近正式开发环境的联调。它会启动：

- PostgreSQL
- Redis
- Qdrant
- FastAPI 后端
- Next.js 前端

如果 Docker Desktop 没有运行，先用方式 A 跑通界面和主流程。

## 环境要求

推荐环境：

- Windows + PowerShell
- Node.js `>=22 <23`
- npm `>=10 <12`
- Python `>=3.11`
- Docker Desktop，可选，仅完整模式需要

项目根目录是运行命令的位置。示例：

```powershell
cd C:\Users\Administrator\Desktop\laiver
```

检查当前工具：

```powershell
node -v
npm.cmd -v
python --version
docker info
```

如果 `docker info` 失败，仍然可以先使用轻量本地模式。

## 第一次准备

### 1. 创建环境变量文件

```powershell
copy .env.example .env
```

默认 `.env.example` 使用 SQLite：

```env
DATABASE_URL=sqlite:///./apps/api/local.db
AUTO_INIT_DB=true
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

如果你只是先把界面跑起来，不需要马上改这些值。

### 2. 安装前端依赖

```powershell
npm.cmd ci
```

如果当前系统 Node 不是 22.x，需要先切换到 Node 22。项目根目录的 `package.json` 开启了 engine 检查，Node 23 会被拒绝。

### 3. 创建 Python 虚拟环境并安装后端依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e "apps/api[dev]"
```

之后同一个 PowerShell 窗口里会使用 `.venv` 的 Python。

## 方式 A：轻量本地启动

推荐使用一行命令启动本机链路：

```powershell
npm.cmd run windows:local
```

这个命令启动后会保持当前 PowerShell 窗口打开，用来监督 API 和 Web 进程。需要停止本机服务时，在这个窗口按 `Ctrl+C`。

启动前可以先运行本机环境检查：

```powershell
npm.cmd run windows:doctor
```

它会自动完成：

- 优先使用项目 `.venv` 中的 Python。
- 优先使用项目 `.tmp\tools` 下的 Node 22 便携版。
- 创建或读取 `.env`。
- 强制使用 SQLite 本地数据库。
- 后台启动 API 和 Web。
- 检查 API health 和 Web 首页。
- 打印访问地址和日志目录。

启动成功后打开：

```text
http://localhost:3000
```

如果你不想自动打开浏览器：

```powershell
npm.cmd run windows:local -- -NoBrowser
```

如果你希望启动后命令直接返回：

```powershell
npm.cmd run windows:local -- -Detach
```

如果使用了 `-Detach` 或者需要单独停止本机服务：

```powershell
npm.cmd run windows:local:stop
```

日志位置：

```text
.tmp/run-logs/local-api.out.log
.tmp/run-logs/local-api.err.log
.tmp/run-logs/local-web.out.log
.tmp/run-logs/local-web.err.log
```

确认 API 是否可用：

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
```

如果你想手动分两个窗口启动，也可以这样做：

```powershell
.\.venv\Scripts\Activate.ps1
npm.cmd run windows:dev:api -- -UseSqlite
```

另一个窗口：

```powershell
npm.cmd run windows:dev:web
```

## 方式 B：Docker 完整启动

确认 Docker Desktop 已启动：

```powershell
docker info
```

启动基础设施：

```powershell
npm.cmd run windows:infra:up
```

如果你要连同 API 和 Web 容器一起启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\Start-AgentInfra.ps1 -IncludeAppContainers
```

如果只启动 PostgreSQL / Redis / Qdrant，并在本机跑 API 和 Web，继续执行迁移：

```powershell
npm.cmd run windows:db:migrate
```

再分别启动后端和前端：

```powershell
npm.cmd run windows:dev:api
npm.cmd run windows:dev:web
```

停止 Docker 服务：

```powershell
npm.cmd run windows:infra:down
```

如果你明确想删除 Docker volume 中的数据：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\Stop-AgentInfra.ps1 -RemoveVolumes
```

## 配置模型

Laiver 当前支持：

- DeepSeek
- OpenAI-compatible API
- Ollama
- Local Adapter

首次试用时，即使没有 API Key，系统也可以走 mock fallback，方便先验证页面和主链路。

要使用 DeepSeek，在 `.env` 中填写：

```env
DEEPSEEK_API_KEY=你的 key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

然后重启 API。

你可以在 Settings 页面管理 provider：

```text
http://localhost:3000/settings
```

也可以运行 DeepSeek live check：

```powershell
npm.cmd run windows:deepseek:check
```

## 第一次实际使用

推荐从 Onboarding 页面开始：

```text
http://localhost:3000/onboarding
```

按页面顺序完成：

1. 上传聊天记录文件。
2. 预览解析出的 normalized messages。
3. 提交 import 入库。
4. 选择目标 speaker。
5. 生成 Persona。
6. 创建 fine-tune job，先只创建和预览，不必马上启动训练。
7. 初始化默认模型 provider 和内置 Skills。
8. 跳转到 Chat 页面发起测试对话。

当前导入支持：

- `txt`
- `csv`
- `json`
- `xlsx`

其中 `xlsx` 重点支持类似 WeFlow 导出的微信聊天记录格式。

## 各页面怎么用

### Imports

地址：<http://localhost:3000/imports>

用于单独测试聊天记录导入。你可以上传文件，查看解析预览，再提交为 import job。提交后的数据会被 Persona、Training 和 Chat 复用。

### Persona

地址：<http://localhost:3000/persona>

用于从导入消息中抽取某个 speaker 的表达风格。微信双人聊天里，建议明确选择对方作为目标 speaker，避免把自己的说话风格混进去。

Persona 当前包含：

- 语气
- 详细程度
- 常见表达
- 常见话题
- 回复风格
- 关系风格
- 证据片段

### Chat

地址：<http://localhost:3000/chat>

用于测试 Agent 回复。页面会显示与调试相关的信息，包括：

- 当前模型 provider
- 是否触发 fallback
- 使用的 Persona
- 召回的 memory
- Skill 调用情况
- 长对话摘要和 trace 信息

### Memories

地址：<http://localhost:3000/memories>

用于查看长期记忆系统的调试状态。当前支持：

- memory 列表
- episode ledger
- fact ledger
- revision history
- candidate review queue
- conflict groups
- user profile snapshot
- relationship state snapshot
- 手动运行 maintenance

低置信、敏感或需要审核的记忆会先进入候选队列，不会直接写成长期事实。

### Settings

地址：<http://localhost:3000/settings>

用于管理模型 provider。你可以创建、启用、设置默认 provider，并查看健康检查、route policy 和 fallback 状态。

### Skills

地址：<http://localhost:3000/skills>

用于管理内置 Skill 和受控社区 Skill。当前支持：

- 初始化内置 Skill
- 上传 `skill.json`
- 上传包含 `skill.json` 的 `.zip`
- 启用 / 停用 / 删除 Skill
- 查看调用日志

社区 Skill 当前是安全受控版本，暂不支持无沙箱执行任意第三方代码。

### Connectors

地址：<http://localhost:3000/connectors>

当前已有 Feishu Connector MVP，用于验证：

- webhook 入站消息
- conversation mapping
- Agent 回复出站
- mock / live 模式切换
- delivery log

### Training

地址：<http://localhost:3000/training>

用于从已导入聊天记录创建本地 LoRA / QLoRA 训练任务。当前默认基座模型选定为 `Qwen/Qwen3-14B`，目标是在 16GB 显存机器上优先使用 QLoRA 训练角色风格 adapter。

当前建议先使用 Training 页面生成和检查训练数据集；真正启动训练前，需要确认 NVIDIA 驱动、CUDA、WSL2/Linux 训练环境、Python 训练依赖、模型权重下载和磁盘空间都准备好。Windows 原生链路可以继续负责 Web/API/DeepSeek 使用，但 QLoRA 训练建议放到 WSL2 或 Linux 中执行。

## 推荐验收流程

如果你想确认本地部署是否真的可用，按这个顺序走一遍：

1. 打开首页：<http://localhost:3000>
2. 打开 Onboarding。
3. 上传一份小聊天记录文件。
4. 预览并提交 import。
5. 选择目标 speaker 并生成 Persona。
6. 初始化模型 provider 和 Skills。
7. 到 Chat 页面发送一句测试消息。
8. 到 Memories 页面查看是否有写入、候选记忆或 trace。
9. 到 Settings 页面检查当前 provider 和 fallback 状态。

这条路径跑通，就说明本地核心链路已经可用。

## 常用命令

```powershell
# 安装依赖
npm.cmd ci
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e "apps/api[dev]"

# 本地检查
npm.cmd run windows:doctor

# SQLite 轻量启动
npm.cmd run windows:local
npm.cmd run windows:local:stop
npm.cmd run windows:dev:api -- -UseSqlite
npm.cmd run windows:dev:web

# Docker 基础设施
npm.cmd run windows:infra:up
npm.cmd run windows:db:migrate
npm.cmd run windows:infra:down

# 验证
npm.cmd run lint:api
npm.cmd run test:api
npm.cmd run eval:memory
npm.cmd run typecheck:web
npm.cmd run build:web
npm.cmd run check
python scripts/run_mvp_regression.py
```

## 常见问题

### 页面打不开

先确认端口是否在监听：

```powershell
netstat -ano | findstr ":3000 :8000"
```

再确认 API：

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
```

如果 API 没起来，先看启动 API 的 PowerShell 窗口错误。

### npm 安装失败，提示 Node 版本不符合

项目要求 Node.js `>=22 <23`。切到 Node 22 后重新运行：

```powershell
npm.cmd ci
```

### Docker 启动失败

确认 Docker Desktop 已经打开，并且 `docker info` 能正常返回。如果 Docker 暂时不可用，先使用 SQLite 轻量模式。

### 修改 `.env` 后没有生效

需要重启 API。前端的 `NEXT_PUBLIC_API_BASE_URL` 也需要在 Web 启动前设置好。

### 没有模型 API Key 能不能用

可以先用 mock fallback 跑通导入、Persona、页面和调试链路。要验证真实模型回复，再到 `.env` 配置 DeepSeek、OpenAI-compatible、Ollama 或 Local Adapter。

### 本地训练能不能直接点启动

可以创建和预览训练任务，但真正训练会占用本地计算资源。当前选定方案是 `Qwen/Qwen3-14B` + QLoRA；16GB 显存可以尝试，但需要保守 batch、context window 和梯度累积设置。建议先确认 GPU、显存、CUDA、WSL2/Linux、模型权重和 Python 训练依赖，再在 Training 页面启动。

## 当前完成度

已经具备：

- 聊天记录导入预览与提交
- WeFlow-like 微信 `xlsx` 支持
- normalized message 标准化
- Persona 抽取
- Agent Chat 编排
- 长期 Memory V2 基础结构
- candidate review queue
- memory maintenance
- 模型 provider 管理和 fallback trace
- 本地 fine-tune job 与 dataset preview
- Skill 安装和管理
- Feishu Connector MVP
- Onboarding 主流程页面

仍在完善：

- 更多微信导出格式
- 大文件异步导入和断点续传
- 真实 GPU 训练稳定性和效果评估
- 更完整的模型 health cache、fallback policy 和多 provider 路由
- memory rollback、merge、privacy tier
- Skill marketplace、签名校验、权限审核和沙箱执行
- Feishu 之外的连接器
- 产品级 UI polish 和新手引导细节
