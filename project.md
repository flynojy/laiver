# Laiver 项目基线

最后更新日期：2026-05-11

本文档是后续修改、排期和 Agent 协作的项目基底。它基于当前仓库代码、README、`agent.md`、架构文档、ADR、Memory 计划文档、测试入口和一次本地验证尝试整理。除非有新的代码或测试结果覆盖，后续应以本文档作为当前状态判断。

后续 Codex / Agent 接手提示词：先阅读本文档和 `agent.md`，复述当前阶段、已完成能力、剩余任务和本轮计划；完成任务后必须在本文档记录进度，并在最终回复说明接下来需要做的工作。

## 1. 项目定位

Laiver 是一个面向个人长期陪伴场景的 personalized AI companion / personal agent 原型。

它的目标不是只做一个聊天壳，而是把真实聊天记录、Persona、长期记忆、模型路由、受控 Skill、本地微调和外部 Connector 串成一条本地可运行、可调试、可继续产品化的工作流。

当前阶段：**MVP+ / early alpha**。

当前判断：

- 核心闭环已经存在，适合继续工程硬化和产品化。
- 当前仍不是生产级系统，不应对外宣称 production ready。
- 近期目标应优先保证可验证、可复现、可解释，再补治理、安全、评估、更多渠道和 UI polish。

核心路径：

```text
import -> persona -> memory -> chat -> skill -> connector -> training/local adapter
```

## 2. 仓库结构

```text
apps/
  api/        FastAPI backend、SQLAlchemy models、Pydantic schemas、routers、services、tests
  web/        Next.js App Router dashboard
packages/
  shared/     前后端共享 TypeScript 类型
docs/
  adrs/       架构决策记录
  plans/      实施计划与进度记录
scripts/
  windows/    Windows-first 本地运维脚本
  local_finetune/
```

主要技术栈：

- 前端：Next.js 15、React 19、TypeScript、Tailwind、lucide-react。
- 后端：FastAPI、Pydantic 2、SQLAlchemy 2、Alembic。
- 存储：PostgreSQL、Redis、Qdrant；本地测试可使用 SQLite fallback。
- 模型：DeepSeek、OpenAI-compatible API、Ollama、Local Adapter。
- 本地运维：Windows + PowerShell + Docker Desktop 优先。

## 3. 已实现能力

### 3.1 Web 页面

当前 dashboard 页面包括：

- `/`：MVP 验收步骤和总览。
- `/onboarding`：首次使用链路，串联上传、预览、Persona、fine-tune job、provider、Skill 初始化。
- `/imports`：上传和预览聊天记录，提交 normalized messages。
- `/persona`：从导入语料抽取和编辑 Persona。
- `/chat`：测试 Agent 回复，查看 provider、memory、skill、fallback、summary 等调试信息。
- `/memories`：查看 Memory V2 debug state、review queue、facts、revisions、profile、relationship，并手动运行 maintenance。
- `/skills`：管理内置 Skill 和受控社区 Skill 包。
- `/connectors`：配置和测试 Feishu Connector。
- `/settings`：管理模型 provider 和 Local Adapter runtime。
- `/training`：创建、预览、启动 fine-tune job，并注册 adapter provider。

### 3.2 API 路由

API 统一挂载在 `/api/v1`，当前 router 包括：

- `health`
- `users`
- `imports`
- `personas`
- `memories`
- `conversations`
- `fine-tuning`
- `skills`
- `connectors`
- `model-providers`
- `agent`

### 3.3 Import

导入支持：

- `txt`
- `csv`
- `json`
- `xlsx`

当前 `xlsx` 重点支持类似 WeFlow 的微信聊天记录导出格式，包含：

- 预览和提交。
- 参与者识别。
- 自己 / 对方 / 系统消息识别。
- normalized message 输出。
- source metadata 保留。
- 后续 Persona 和训练数据复用。

### 3.4 Persona

Persona 可从导入消息中抽取表达风格，支持指定 `source_speaker`，避免把用户本人和目标陪伴对象的风格混在一起。

当前 Persona 字段覆盖：

- 语气。
- 详细程度。
- 常见表达。
- 常见话题。
- 回复风格。
- 关系风格。
- 证据片段。

### 3.5 Agent Chat

Agent 编排链路包括：

- 读取 Persona。
- 拉取 recent conversation context。
- 检索 Memory。
- 获取 active Skills。
- 路由到当前模型 provider。
- 处理 tool calls / Skill invocation。
- 写回消息和记忆。
- 暴露 debug 信息：provider、route、memory hits、memory writes、skills used、fallback status、summary/compression 等。

Mock provider 和 mock fallback 是本地开发路径的一部分，不能在未替代验证方案前移除。

### 3.6 Memory V2

Memory 已从简单 note 表升级为 companion-memory-v2，当前已实现的 MVP 能力包括：

- `memory_episode`：来源事件 ledger。
- `memory_fact`：结构化当前事实。
- `memory_revision`：reinforce / supersede 等历史。
- `user_profile`：用户画像快照。
- `relationship_state`：用户与 persona 的关系状态快照。
- `memory_candidate`：不确定或需审核的记忆候选队列。
- gated write：低置信、敏感或明确要求 review 的写入先进入候选队列。
- candidate approve / reject。
- duplicate reinforcement。
- conflict supersede。
- multi-route retrieval：profile / instruction / episodic 等路线。
- memory debug state。
- maintenance：事实衰减、弱事实归档、过期 candidate 忽略、profile/relationship 重建。

当前仍保留旧 `Memory` 表兼容路径。新 work 应继续尊重增量 dual-write / 迁移策略，避免硬切换破坏已有闭环。

### 3.7 Skills

Skill 系统当前支持：

- 内置 Skill。
- 启用 / 停用。
- 删除。
- 查看 manifest。
- 查看 invocation log。
- 上传 `skill.json`。
- 上传包含 `skill.json` 的 zip 包。
- 通过受控 proxy handler 复用平台允许的本地 handler。

当前不支持无沙箱执行任意第三方代码。

### 3.8 Connectors

当前有 Feishu Connector MVP：

- webhook receive。
- verification token validation。
- message normalization。
- conversation mapping。
- Agent reply handoff。
- delivery logging。
- mock / live mode。
- duplicate message idempotency。

Feishu 现在是后续扩展微信、Telegram、Email 等 Connector 的模板，不代表多渠道已经完成。

### 3.9 Model Providers

当前支持 provider 类型：

- `deepseek`
- `openai_compatible`
- `ollama`
- `local_adapter`

已实现：

- provider registry。
- provider validation。
- 默认 provider bootstrap。
- Chat Completions 风格抽象。
- streaming / tool call payload 支持。
- API key 缺失时的 mock fallback。
- `mock://` transport。
- Local Adapter warm / evict。
- idle cleanup。
- timeout guard。
- resident runtime。

### 3.10 Local Fine-tuning

Training 链路当前支持：

- 从导入消息创建 fine-tune job。
- 选择 speaker。
- 设置 context window。
- train / validation / test split。
- 预览训练样本。
- 导出 JSONL dataset。
- 写入训练配置。
- mock training launch。
- local training script。
- 记录 artifact。
- 将完成 job 注册为 `local_adapter` provider。

## 4. 当前验证状态

`apps/api/tests/test_integration.py` 是当前最重要的可执行规格，覆盖 import、Persona、Agent、Skills、Memory、Connector、Provider、Fine-tuning 和 Local Adapter runtime。

最近一次本地验证结果：

- `.venv/bin/python -m ruff check apps/api --select E9,F63,F7,F82`
  - 结果：通过。
- `.venv/bin/python -m unittest discover -s apps/api/tests -p 'test_*.py'`
  - 结果：通过，48 个集成测试 OK。
- `npm run typecheck:web`
  - 结果：通过，需使用 Node 22。
- `npm run build:web`
  - 结果：通过，需使用 Node 22。
- `npm run check`
  - 结果：通过。执行环境为项目 `.venv` 在 PATH 前、Node 22 在 PATH 前。
- `npm run eval:memory`
  - 结果：通过，7 个 regression eval OK，已覆盖 profile、episodic、exact phrase、chat grounding、duplicate、conflict 和 gated approval。

2026-05-11 本机链路补充：

- 已新增 `npm.cmd run windows:local`，作为 Windows 本机 SQLite 模式的一行启动入口。
- 已新增 `npm.cmd run windows:local:stop`，用于停止本机链路占用的 API/Web 端口。
- `npm.cmd run windows:doctor` 已调整为本机链路优先检查，Docker 不再是默认必需项。
- 当前优先路线调整为：**先稳定本机链路，再做 Docker 容器部署优化**。
- 本机链路依赖 `.venv`、项目内 Node 22 或 PATH 中 Node 22、SQLite `apps/api/local.db`。
- Docker 链路暂不作为近期主线；后续在本机流程稳定后再统一修 Docker Desktop、compose、容器化 API/Web 和持久化卷。

因此当前状态是：**API 与 Web 的基础验证入口已恢复绿色；本机运行链路已经有一行启动脚本；完整 Docker 链路仍需后置优化**。

下一次改动前建议先恢复验证基线：

1. 准备后端 Python 3.11+ 虚拟环境，激活后执行 `python -m pip install -e "apps/api[dev]"`。
2. 确认 Node 22 可用，并执行 `npm.cmd ci` 安装 web workspace 依赖。
3. 先跑通 `npm.cmd run windows:local -- -NoBrowser`，确认本机 API/Web 可启动。
4. 跑通 `npm.cmd run lint:api` 和 `npm.cmd run test:api`。
5. 跑通 `npm.cmd run eval:memory`。
6. 跑通 `npm.cmd run typecheck:web` 和 `npm.cmd run build:web`。
7. 再执行 `python scripts/run_mvp_regression.py`。

## 5. 已知问题与任务池

### P0：验证基线

- 后端 lint 和 integration suite 已可在 `.venv` 中通过。
- 前端 TypeScript `baseUrl` 弃用检查已通过移除 `baseUrl` 处理；Node 22 下 `npm ci`、`npm run typecheck:web`、`npm run build:web` 已通过。
- Windows 本机链路优先使用 `.venv\Scripts\python.exe`，避免依赖全局 Python。
- 本机全局 Node 可能不是 22；`scripts/windows/Start-AgentLocal.ps1` 会优先解析 `.tmp\tools` 下的 Node 22 便携版。
- 需要补充一条本机启动脚本的自动化验证，至少覆盖脚本语法、缺依赖提示、端口占用提示、API/Web health check。

### P0：本机启动链路产品化

- 当前已有 `npm.cmd run windows:local`，可以一行启动 SQLite + API + Web。
- 当前已有 `npm.cmd run windows:local:stop`，用于清理 3000/8000 上看起来属于本项目的进程；不确定归属时会提示，避免误杀其他服务。
- 当前 `npm.cmd run windows:doctor` 已覆盖 `.venv`、Node 22、依赖安装、端口占用、`.env`、SQLite 文件可写性。
- 已补基础错误提示：端口被占用、Node 版本不对、Python 依赖缺失、API 启动失败、Web 启动失败。
- 仍需补脚本级自动化测试，覆盖 doctor / start / stop 的常见分支。
- 后续可把 PowerShell 启动链路包装为 exe，但应在脚本稳定后再做。

### P1：Memory 质量、治理与可解释性

- `memory_service.py` 仍然较集中，可在验证稳定后再拆成更小的 domain services。
- Memory V2 MVP 已落地，regression harness 已纳入 `npm run check`。
- rollback、merge、privacy tier、更完整的 sensitivity controls 尚未完成。
- exact / full-text 基础召回已补齐；中文姓名、专有名词、更长原话片段和更清晰的 memory trace 仍需继续扩展。
- 长期记忆 recall 质量还缺系统化回归集和评估指标。

### P1：模型路由与运行稳定性

- provider health check 仍需加强。
- fallback policy 和 route policy 仍偏 MVP。
- 真实 provider 异常、超时、限流、无 key、mock fallback 的行为需要更明确的策略和测试。
- 需要补一个类似 switchcc 的模型切换界面，用于一键查看、验证、切换当前默认模型 provider，并清楚展示当前 provider、健康状态、fallback 状态和切换结果。
- Local Adapter runtime 已有 warm/evict/timeout guard，但真实模型加载和资源管理还需在目标机器上验证。

### P1：Fine-tuning 效果验证

- 当前已有 dataset/job/artifact/provider 注册链路，但真实 GPU 训练稳定性未验证。
- 显存占用、训练耗时、失败恢复、artifact 兼容性仍需实测。
- 训练效果缺 A/B 对比和质量评估流程。
- 本地 QLoRA 默认模型已选定为 `Qwen/Qwen3-14B`；目标硬件为 16GB 显存机器，真实训练仍需 WSL2/Linux、CUDA、依赖、显存占用和效果验证。

### P2：Import 工程化

- 微信导出格式差异大，目前只重点覆盖类似 WeFlow 的 `xlsx`。
- 大文件异步导入、进度反馈、错误恢复、断点续传尚未完成。
- 更复杂的消息类型、附件、撤回、引用、表情和系统消息处理还需扩展。

### P2：Skill 平台化

- 当前社区 Skill 是受控安装，不支持任意第三方代码执行。
- marketplace、版本更新、签名校验、权限审核、沙箱执行尚未完成。
- Skill 权限模型和安全边界需要进一步产品化。

### P2：Connector 扩展

- 当前只有 Feishu MVP。
- 微信、Telegram、Email 等 Connector 尚未实现。
- Feishu live 模式的生产部署、回调稳定性、失败重试和可观测性仍需加强。

### P2：产品体验

- 当前 Web 更像操作型 dashboard 和 debug console。
- Onboarding 的错误提示、状态反馈、空状态、失败恢复和新手引导仍需 polish。
- Memory、Training、Connector 页面需要面向普通用户降低理解成本。
- UI 不能改成营销 landing page，首屏应继续服务实际操作流。

## 6. 推荐近期路线

建议后续按下面顺序推进，先把本机用户路径做扎实，再扩展 Docker 和更重的生产化能力：

1. 跑一次完整本机验收：`windows:doctor` -> `windows:local` -> Onboarding -> Import -> Persona -> Chat -> Memory -> Settings -> `windows:local:stop`。
2. 补本机脚本自动化测试，覆盖 doctor / start / stop 的语法、缺依赖、端口占用和 health check 分支。
3. 把 `agent.md` 中的命令同步到 Windows 本机优先口径。
4. 强化模型设置体验：切换前自动 validate、失败回滚提示、provider health cache、独立模型管理入口。
5. 继续细化 fallback policy：`none` 策略错误语义、备用 provider 链路、多 provider health cache、真实 DeepSeek/Ollama/Local Adapter live check。
6. 强化 Memory 可解释性：更清晰 memory trace、中文姓名/专有名词/长原话片段 regression、rollback/merge/privacy tier。
7. 做 Onboarding / Chat / Memory / Settings 的产品体验 polish，优先改善真实使用路径，不做营销页。
8. 验证 local fine-tuning：真实 GPU、显存、耗时、失败恢复、artifact 兼容性和 A/B 效果评估。
9. Import 工程化：更多微信导出格式、大文件异步、进度反馈、错误恢复、断点续传、附件/撤回/引用/表情。
10. Docker 后置优化：修 Docker Desktop 环境、compose 全链路、PostgreSQL/Redis/Qdrant 持久化、容器健康检查、容器化 API/Web。
11. Skill 平台化：marketplace、版本更新、签名校验、权限审核和沙箱执行。
12. Connector 扩展：先稳定 Feishu live，再考虑微信、Telegram、Email。

## 7. 协作约定

- 每次接手任务先做规划、理解和影响分析，再进行代码或文档修改。
- 每次对话结束在最终回复中说明接下来需要做的工作。
- 每次完成任务都在本文档追加或更新进度备注，便于对话中断后续接。
- Codex / Agent 协作细则见 `agent.md`；接手新任务时必须同时阅读本文档和 `agent.md`。
- 开发时优先保持模块解耦，新增能力应明确归属到 domain service、schema、router、前端组件或共享类型边界，避免后续新增模块和修改模块变困难。
- 新增或变更对外接口时，必须同步记录到本文档的接口规范区或相关计划文档，说明 endpoint、请求/响应 shape、使用场景和兼容性注意事项。
- 改后端行为前，先读 `apps/api/tests/test_integration.py`。
- 改 API shape 时，通常需要同步：
  - `apps/api/app/schemas`
  - `apps/web/lib/api.ts`
  - `packages/shared/src/types.ts`
- 改 Memory 行为时，保留旧 `Memory` 表兼容路径，并尊重 V2 episode / fact / revision / profile / candidate 结构。
- 改模型能力时，保留 mock provider、mock fine-tune 和 Local Adapter mock runtime。
- 改 Connector 行为时，保留 Feishu token 校验、delivery log、conversation mapping 和幂等处理。
- 改前端时，把它当作工作台和调试控制台，不要改成 marketing page。
- 不要回滚无关文件或重排大范围格式。

## 8. 常用命令

Windows-first 路径：

```powershell
npm.cmd ci
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e "apps/api[dev]"
npm.cmd run windows:doctor
npm.cmd run windows:local
npm.cmd run windows:local:stop
```

Docker 完整链路后置：

```powershell
npm.cmd run windows:infra:up
npm.cmd run windows:db:migrate
npm.cmd run windows:dev:api
npm.cmd run windows:dev:web
npm.cmd run windows:deepseek:check
npm.cmd run windows:infra:down
```

前端验证：

```powershell
npm.cmd ci
npm.cmd run typecheck:web
npm.cmd run build:web
```

后端验证：

```powershell
python -m pip install -e "apps/api[dev]"
npm.cmd run lint:api
npm.cmd run test:api
npm.cmd run eval:memory
python scripts/run_mvp_regression.py
```

注意：当前项目优先走 Windows 本机链路。前端命令必须使用 Node 22；后端命令优先使用项目 `.venv`。

## 9. 关键参考文件

- `README.md`
- `agent.md`
- `docs/architecture.md`
- `docs/adrs/0001-mvp-foundation.md`
- `docs/adrs/0006-companion-memory-v2.md`
- `docs/plans/2026-04-04-windows-first-operations.md`
- `docs/plans/2026-04-23-laiver-memory-system-implementation-plan.md`
- `docs/plans/2026-04-23-memory-eval-matrix.md`
- `apps/api/tests/test_integration.py`

## 10. 接口规范

### Model Provider API

- `GET /api/v1/model-providers`：列出 provider registry，用于 Settings / 模型切换 UI 展示可选模型。
- `POST /api/v1/model-providers`：创建 provider；请求体使用 `ModelProviderCreate`，包括 `name`、`provider_type`、`base_url`、`model_name`、`api_key_ref`、`settings`、`is_default`、`is_enabled`。当 `is_default=true` 时，会取消其他默认 provider 并启用当前 provider。
- `PATCH /api/v1/model-providers/{provider_id}`：更新 provider；常用于一键切换默认模型、启停 provider、更新 settings。切换默认 provider 时传 `{"is_default": true}`。
- `POST /api/v1/model-providers/bootstrap`：若尚无默认 provider，则创建 DeepSeek 默认 provider，读取 `DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL` 和 `env:DEEPSEEK_API_KEY`。
- `POST /api/v1/model-providers/validate`：验证 provider 健康状态；响应包含 `health_status`、`route_policy`、`fallback_policy`、`fallback_available`、completion/stream/tool 结果和错误信息。
- `POST /api/v1/model-providers/complete`：直接调用 provider completion；响应包含 `route_policy`、`fallback_policy`、`fallback_used`、`fallback_reason` 和 `attempted_providers`，用于调试路由与降级。
- `POST /api/v1/model-providers/stream`：直接调用 provider streaming；当前返回 `text/plain` chunk。
- `GET /api/v1/model-providers/local-adapters/runtime`、`POST /api/v1/model-providers/{provider_id}/warm`、`POST /api/v1/model-providers/{provider_id}/evict`：Local Adapter runtime 管理接口。

兼容性注意：当前 DeepSeek / OpenAI-compatible 走 Chat Completions 兼容协议，即 `POST {base_url}/chat/completions`；暂未接 OpenAI Responses API。模型切换 UI 应优先复用上述接口，不直接绕过后端读写数据库。

## 11. 进度备注

### 2026-05-08：补充 Agent 续接协作规则

- 当前阶段确认：项目处于 MVP+ / early alpha，核心链路已存在，最近完成 memory exact recall regression 并保持本地验证基线绿色记录。
- 本轮完成：在 `agent.md` 增加接手前先规划理解分析、结束时说明下一步、完成后更新 `project.md` 的协作要求。
- 本轮完成：在本文档增加 Codex / Agent 接手提示词，并把 `agent.md` 作为协作细则入口。
- 下一步建议：按推荐近期路线继续推进 memory trace / provider health check 与 fallback policy；改动前先重新跑当前验证基线。

### 2026-05-08：提交协作规则并恢复验证基线

- 本轮完成：提交 `Document agent handoff workflow`，提交号 `118f01f`。
- 本轮验证：使用 `PATH=/opt/homebrew/opt/node@22/bin:.venv/bin:$PATH npm run check` 跑完整基线，通过 API lint、48 个后端集成测试、7 个 memory regression、Web typecheck 和 Web production build。
- 环境备注：全局 Node 仍是 v25.9.0；验证时需要显式把 Node 22 和 `.venv/bin` 放到 PATH 前。
- 下一步建议：开始 P1 任务，优先强化 provider health check / fallback policy / route policy，或继续扩展 memory trace 与 exact/full-text regression。

### 2026-05-09：强化模型路由健康检查与降级可解释性

- 本轮完成：`ModelRouterService` 增加 route policy、fallback policy、provider failure classification、attempted providers 和 mock fallback metadata；真实 provider 不可达时 completion/Agent 路径会返回可解释 mock fallback，而不是直接 500。
- 本轮完成：`/model-providers/validate` 增加 `health_status`、`fallback_available`、`route_policy`、`fallback_policy`，Settings 页面同步展示健康和降级状态。
- 本轮完成：Agent debug 增加 provider fallback 信息，方便 Chat / Connector trace 判断是否由模型不可达触发降级。
- 本轮测试：新增 provider validation unhealthy、completion fallback、Agent default provider fallback 等集成测试；完整 `PATH=/opt/homebrew/opt/node@22/bin:.venv/bin:$PATH npm run check` 通过，当前集成测试 51 个、memory regression 7 个。
- 下一步建议：继续细化 fallback policy 的可配置行为，例如 `none` 策略的 API 错误语义、备用 provider 链路、多 provider health cache，以及真实 DeepSeek/Ollama/Local Adapter live check。

### 2026-05-09：配置本地 DeepSeek 测试 Key 并记录模型切换界面需求

- 本轮完成：创建本地 `.env` 并配置 `DEEPSEEK_API_KEY`；`.env` 已被 `.gitignore` 忽略，不应提交密钥。
- 本轮验证：通过 `get_settings()` 确认 `deepseek_key_configured=True`，DeepSeek base URL 为 `https://api.deepseek.com`，模型为 `deepseek-chat`。
- 本轮记录：后续需要做类似 switchcc 的模型切换界面，支持一键切换默认 provider、验证 provider 健康状态、显示 fallback/route 信息，并让用户明确当前 Chat 使用哪个模型。
- 下一步建议：先用 `/api/v1/model-providers/bootstrap` 创建 DeepSeek 默认 provider，再调用 `/api/v1/model-providers/validate` 做 live check；随后实现模型切换 UI。

### 2026-05-09：补充接口规范、DeepSeek live check 和模型切换 UI 第一版

- 本轮完成：在 `agent.md` 和本文档补充工程约束，明确开发中优先保持模块解耦，新增/变更对外接口必须同步记录接口规范。
- 本轮完成：新增 Model Provider API 接口规范，记录 provider registry、bootstrap、validate、complete、stream 和 Local Adapter runtime 相关 endpoint。
- 本轮完成：修正 `env:DEEPSEEK_API_KEY` 解析逻辑，优先读系统环境变量，缺失时回退到 Settings 从 `.env` 加载的 DeepSeek key；同时隔离集成测试，避免本地 `.env` 影响 mock fallback 基线。
- 本轮验证：使用本地 DeepSeek key 对 `/model-providers/validate` 做 live check，结果 `health_status=healthy`、`completion_ok=True`、`completion_preview=pong-live`。
- 本轮完成：新增可复用 `ModelSwitcher` 前端组件，并在 Settings 页面提供当前默认模型、健康/fallback 状态、一键检查和一键切换默认 provider 的第一版 UI。
- 本轮测试：完整 `PATH=/opt/homebrew/opt/node@22/bin:.venv/bin:$PATH npm run check` 通过，当前集成测试 52 个、memory regression 7 个。
- 下一步建议：把模型切换 UI 从 Settings 中进一步产品化，例如增加 Provider health cache、切换前自动 validate、失败回滚提示，以及独立的模型管理/切换快捷入口。

### 2026-05-09：推送前进度汇总

- 当前仓库状态：`main` 已包含协作续接规则、模型路由 fallback tracing、DeepSeek 本地配置记录、接口规范和模型切换 UI 第一版；本地 `.env` 存有 DeepSeek 测试 key，但 `.env` 被 `.gitignore` 忽略，不会上传。
- 当前验证基线：最近完整 `PATH=/opt/homebrew/opt/node@22/bin:.venv/bin:$PATH npm run check` 已通过，覆盖 API lint、52 个集成测试、7 个 memory regression、Web typecheck 和 Web production build。
- 当前 live 能力：DeepSeek provider 通过 `/model-providers/bootstrap` 和 `/model-providers/validate` 可完成 live check，结果曾验证为 `health_status=healthy`、`completion_preview=pong-live`。
- 未来 P1：模型切换 UI 继续产品化，增加切换前自动 validate、失败回滚提示、provider health cache、独立快捷入口或模型管理页。
- 未来 P1：继续细化 fallback policy，包括 `none` 策略的 API 错误语义、备用 provider 链路、多 provider health cache、真实 DeepSeek/Ollama/Local Adapter live check。
- 未来 P1：继续强化 Memory 可解释性，补更清晰 memory trace、中文姓名/专有名词/长原话片段 regression、rollback/merge/privacy tier。
- 未来 P1：真实 GPU 环境验证 local fine-tuning，补显存/耗时/失败恢复、artifact 兼容性和 A/B 效果评估。
- 未来 P2：Import 工程化，补更多微信导出格式、大文件异步、进度反馈、错误恢复、断点续传、附件/撤回/引用/表情等复杂消息。
- 未来 P2：Skill 平台化，补 marketplace、版本更新、签名校验、权限审核和沙箱执行。
- 未来 P2：Connector 扩展，在 Feishu 稳定后补微信、Telegram、Email，并增强 live 部署、重试和可观测性。
- 未来 P2：Dashboard 产品体验 polish，重点改善 Onboarding、Memory、Training、Connector 页面，不改成营销页。

### 2026-05-11：整理用户态 README 部署与使用教程

- 本轮完成：重写 `README.md` 为面向用户的部署到实际使用教程，按轻量 SQLite 本地模式、Docker 完整模式、模型配置、首次使用、页面说明、验收流程和常见问题组织。
- 本轮完成：新增 `scripts/windows/Start-AgentLocal.ps1` 和 `npm.cmd run windows:local`，作为本机 SQLite 链路的一行启动入口；脚本会解析 `.venv`、Node 22、`.env`，启动 API/Web 并做健康检查。
- 本轮完成：补充 `scripts/windows/Stop-AgentLocal.ps1`、`npm.cmd run windows:local:stop`，并把 `windows:doctor` 调整为本机链路优先的环境诊断。
- 本轮完成：新增 `docs/fixtures/simulated-yokohama-yandere-chat.csv`，作为虚构聊天记录导入样例；已用 import parser 验证为 124 条 CSV 消息，参与者为 `我` 和 `神崎澪`。
- 本轮说明：未修改应用源码；文档基于当前 Windows 脚本、`.env.example`、`docker-compose.yml`、Web 页面和 API 路由整理。
- 下一步建议：如果要继续产品化文档，可补充真实示例聊天记录、截图、Feishu live webhook 配置步骤，以及 Docker Desktop 故障排查页。

### 2026-05-12：中文化本机 mock fallback 回复

- 本轮完成：修正 Agent mock fallback 默认回复，避免把 `Mock mode is active`、`Current persona focus` 等调试英文模板暴露给用户；调试状态继续保留在 debug 字段。
- 本轮完成：memory grounding、task grounding、skill error fallback 的用户可见提示改为中文。
- 本轮测试：相关集成测试通过，包括默认 mock 中文回复、provider 不可达 fallback、memory grounding、task extractor grounding 和 skill failure fallback。
- 本轮实测：本机服务重启后，发送 `你好` 返回 `早安。看到你发来消息，我就安心一点。...`，debug 显示仍为 `mock_provider_default` / `api_key_missing`。

### 2026-05-12：增强本机 mock 对话的基础回应能力

- 本轮完成：为 Agent mock fallback 增加轻量中文对话策略，能自然处理打招呼、`我喜欢吃 X` 和 `我喜欢吃什么` 这类本机验收常见对话。
- 本轮完成：为 memory-search 触发词补充中文 recall hint，例如 `我喜欢什么`、`我喜欢吃什么`、`记得`。
- 本轮测试：新增并通过 `test_mock_conversation_answers_simple_preference_followup`，覆盖 `你好 -> 我喜欢吃冰淇淋 -> 我喜欢吃什么呀`。
- 本轮实测：本机服务重启后，追问 `我喜欢吃什么呀` 返回 `你喜欢冰淇淋。我记住了。`。
### 2026-05-12: Qwen think gate strategy

- Default to `think=false` for fast replies, greetings, short confirmations, and fixed-format answers.
- Add a lightweight preflight gate before provider execution to classify each request as `fast_reply`, `need_reasoning`, or `tool_or_memory_heavy`.
- Enable `think=true` only when the request is ambiguous, multi-step, tool-heavy, memory-conflict-heavy, or explicitly asks for reasoning.
- Record the gate decision in debug output so later traces can explain why thinking was enabled or skipped.
- First target: Ollama `qwen3:14b`, using the native `/api/chat` `think` field.

### 2026-05-12: Qwen think gate implementation

- 本轮完成：Ollama provider 默认在 `/api/chat` 顶层发送 `think=false`，避免 Qwen3 简短对话先进入长思考导致回复空白或延迟。
- 本轮完成：新增轻量 preflight gate，按 `fast_reply`、`need_reasoning`、`tool_or_memory_heavy` 分类；provider settings 中的 `think`、`ollama_think`、`enable_thinking`、`think_mode` 会优先生效。
- 本轮完成：Agent debug 和 Chat 页面展示 `think on/off` 与 gate 名称，方便后续观察什么时候启动思考模式。
- 本轮完成：`windows:ollama:check` 生成测试默认带 `think=false`，更适合 Qwen3 本机链路快速验收。
- 本轮验证：新增并通过 Ollama think gate 相关后端测试，Web typecheck 通过。

### 2026-05-12: frontend decoupling first slice

- 本轮目标：为后续 UI 重铸降低前后端耦合，先不改后端 API，不改变页面行为。
- 本轮完成：新增 `apps/web/features/chat/view-models.ts` 和 `apps/web/features/chat/mappers.ts`，把 `AgentChatResponse`、`MemoryRecord.metadata`、skill invocation 等后端 DTO 映射为 Chat 专用 ViewModel。
- 本轮完成：`/chat` 页面改为渲染 Chat ViewModel，不再直接读取 `lastRun.debug.*` 或 memory metadata；后端 DTO 只集中出现在 feature mapper 中。
- 本轮完成：把 conversation controls 的默认值与归一化逻辑移入 Chat feature 层，页面只消费产品态 controls。
- 本轮验证：`npm.cmd run typecheck:web` 与 `npm.cmd run build:web` 均通过。
- 下一步建议：按同样模式继续改 Settings/provider 和 Memories 页面，把 provider settings、local adapter runtime、memory debug metadata 收敛到各自 feature mapper。

### 2026-05-12: provider settings decoupling slice

- 本轮目标：继续降低 UI 重铸风险，把 Settings/provider 页面从后端 provider schema、validation schema 和 local adapter runtime schema 中解耦出来。
- 本轮完成：新增 `apps/web/features/providers/view-models.ts` 和 `apps/web/features/providers/mappers.ts`，集中定义 ProviderCard、Validation、LocalAdapterRuntime 和 ProviderForm 的产品态 ViewModel。
- 本轮完成：`components/model-switcher.tsx` 改为消费 Provider ViewModel，不再直接依赖 `ModelProviderConfig` 或 `ModelProviderValidationResult`。
- 本轮完成：`/settings` 页面改为从 provider feature mapper 获取渲染数据；Ollama 默认 `think=false`、`num_ctx`、`num_predict` 等后端写入细节收敛在创建 payload 附近，不散落在展示逻辑里。
- 本轮修复：顺手清理 Settings provider preset 文案中的编码异常，替换为可读中文说明。
- 本轮验证：`npm.cmd run typecheck:web` 与 `npm.cmd run build:web` 均通过。
- 下一步建议：继续处理 Memories 页面，把 `MemoryRecord.metadata`、debug state、candidate/revision/fact 展示收敛到 `features/memories` mapper。

### 2026-05-12: memory UI decoupling slice

- 本轮目标：把 Memory 页面从 `MemoryRecord.metadata`、memory debug DTO、fact/revision/candidate 原始字段中解耦，方便后续重铸 Memory UI。
- 本轮完成：新增 `apps/web/features/memories/view-models.ts` 和 `apps/web/features/memories/mappers.ts`，集中定义 MemoryItem、Episode、Fact、Revision、Candidate、ConflictGroup、ProfileSnapshot 和 Dashboard ViewModel。
- 本轮完成：`/memories` 页面改为渲染 Memory ViewModel；label/source/state/score/dedupe/profile bucket/ledger 展示字段不再散落读取后端 metadata。
- 本轮完成：memory state 更新通过 `buildMemoryStatePatch` 生成后端 patch，页面不再手写 metadata merge 逻辑。
- 本轮说明：页面仍在 API 调用边界处发送 `memory_type`、读取 debug DTO 后立即映射，这是当前 REST DTO 边界的合理保留。
- 本轮验证：`npm.cmd run typecheck:web` 与 `npm.cmd run build:web` 均通过。
- 下一步建议：继续把 Imports/Training/Onboarding 页面切成 feature adapter；之后可考虑 OpenAPI 生成 DTO 类型，把 `packages/shared` 的手写后端影子类型降到最低。

### 2026-05-13: frontend feature client boundary

- Completed: added feature-level `client.ts` modules under `apps/web/features/*` so dashboard pages import request functions from their own feature boundary instead of directly from `apps/web/lib/api.ts`.
- Completed: exported `API_BASE_URL` and `apiFetch` from `apps/web/lib/api.ts` as the shared transport layer.
- Completed: `apps/web/features/imports/client.ts` now owns its concrete import endpoints directly; other feature clients currently delegate to `lib/api.ts` and can be migrated incrementally with the same pattern.
- Completed: mapper type imports for Imports, Training, Persona, and Onboarding now reference feature clients rather than `@/lib/api`, keeping DTO knowledge inside feature boundaries.
- Verification: `npm.cmd run typecheck:web` and `npm.cmd run build:web` both passed.
- Next: gradually move endpoint implementations from `apps/web/lib/api.ts` into each feature client, then shrink `lib/api.ts` to transport plus truly shared DTO helpers.
