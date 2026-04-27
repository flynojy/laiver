# Laiver 项目状态

最后研读日期：2026-04-28

## 一句话目标

Laiver 的目标是成为一个本地可运行的 personalized AI companion / personal agent 平台：它能从用户导入的聊天记录中学习表达风格，形成 Persona，长期记忆偏好与关系上下文，通过可配置模型回复，并通过 Skills 与外部连接器扩展能力。

## 目标需求

项目要解决的核心需求不是“能聊天”，而是“能把个人长期陪伴 Agent 的关键链路串起来”：

1. 导入真实聊天记录。
2. 将不同格式消息标准化为可复用结构。
3. 从目标 speaker 中抽取可编辑 Persona。
4. 将偏好、指令、事件和关系上下文沉淀为长期记忆。
5. 通过可配置模型 provider 生成回复。
6. 通过 Skill 执行受控工具能力。
7. 通过 Connector 接入外部通信渠道。
8. 在需要时生成本地微调数据集和 adapter，让模型更贴近目标风格。

当前产品判断：优先保证本地闭环和可调试性，再逐步补齐生产稳定性、治理、安全、评估和更多渠道。

## 当前阶段

当前阶段：**MVP+ / early alpha**。

已存在并被代码覆盖的本地核心路径是：

```text
import -> persona -> memory -> chat -> skill -> connector -> training/local adapter
```

项目已经适合继续产品化和工程硬化，但还不能按生产系统交付。

## 仓库构成

```text
apps/
  api/        FastAPI backend、models、schemas、routers、services、tests
  web/        Next.js dashboard
packages/
  shared/     shared TypeScript contracts
docs/
  adrs/       architecture decisions
  plans/      implementation plans and progress notes
scripts/
  windows/    Windows-first local operations
  local_finetune/
```

## 主要用户工作流

### Onboarding

`/onboarding` 串联首次使用路径：

- 上传聊天记录。
- 预览 normalized messages。
- 选择目标 speaker。
- 抽取 Persona。
- 创建本地 fine-tune 数据集。
- 初始化模型 provider 和 Skills。
- 进入 chat 测试。

### Import

导入支持 `txt`、`csv`、`json` 和 `xlsx`。当前 `xlsx` 重点支持类似 WeFlow 的微信导出格式，包含参与者识别、自己/对方/系统消息分类、source metadata 和标准化输出。

### Persona

Persona 流程从导入消息中抽取表达风格。当前支持指定 `source_speaker`，避免把用户本人和目标陪伴对象的表达风格混在一起。

### Chat

Chat 通过 agent orchestrator 执行：

- 读取 Persona。
- 拉取最近上下文。
- 召回 Memory。
- 调用 active Skills。
- 路由到模型 provider。
- 写回消息和记忆。
- 暴露 provider、route、memory hits、memory writes、skills used 等 debug 信息。

### Memory

Memory 已从简单笔记升级为 companion-memory-v2：

- source episodes
- structured facts
- revisions for reinforcement / supersede
- user profile snapshot
- relationship state snapshot
- review candidates
- gated writes
- decay / maintenance
- debug UI visibility

### Skills

Skill 系统支持内置 Skills 和受控社区 Skill 安装，可通过 `skill.json` 或 zip 包安装、启用、停用、删除、查看 manifest 和 invocation log。当前还不支持无沙箱执行任意第三方代码。

### Model Providers

模型注册表支持：

- DeepSeek
- OpenAI-compatible API
- Ollama
- Local Adapter

Local Adapter 支持 runtime warm/evict、idle cleanup、timeout guard，以及从完成的 fine-tune job 注册为 provider。

### Training

Training 流程可以从导入对话创建本地 LoRA / QLoRA job，预览和导出训练数据，执行 mock/local launch，记录 artifact，并将完成后的 adapter 注册成模型 provider。

### Connectors

Connector 层当前有 Feishu MVP：

- webhook receive
- verification token validation
- message normalization
- conversation mapping
- agent reply handoff
- delivery logging
- mock/live mode
- duplicate message idempotency

## 当前完成情况

已经完成的基础：

- Monorepo 结构：API、Web、shared contracts、docs、scripts。
- Windows-first 运维脚本和根目录 `npm` 命令。
- API routers：health、users、imports、personas、memories、conversations、fine-tuning、skills、connectors、model-providers、agent。
- 覆盖主要工作流的 dashboard 页面。
- 集成测试覆盖导入、Persona、Agent、Skills、Memory、Connectors、Model Providers、Fine-tuning、Local Adapter runtime。
- Memory V2 迁移、模型、schema、API、debug state、review queue 和 maintenance。
- README、architecture、ADR、plans 已记录当前目标与演进方向。

部分完成或仍有风险：

- `memory_service.py` 仍然较集中；计划里提到拆成更细的 memory domain services，但当前还没有完全拆分。
- Memory V2 已具备 MVP 行为，但 rollback、merge、privacy tier、完整 governance 和 benchmark evaluation 仍未完成。
- 本地 fine-tuning 有 job、dataset、artifact 和 adapter 注册链路，但真实 GPU 稳定性、训练效果和 A/B 评估仍待验证。
- 模型 provider 已可注册和路由，但 health check、fallback 和生产级 route policy 仍待完善。
- Feishu connector 可作为模板，但微信、Telegram、Email 等其他渠道尚未实现。
- 社区 Skill 当前是受控安装，marketplace、签名、权限审核和沙箱执行仍是后续目标。
- 大文件导入、异步任务和断点续传尚未完成。

## 验证状态

仓库中 `apps/api/tests/test_integration.py` 是当前最重要的可执行规格，覆盖：

- imports 与微信 `xlsx`
- persona extraction
- agent response
- skill install / invocation
- memory search、review queue、gating、decay、reinforcement、supersede、recall
- connector mapping / delivery
- model provider registry / validation
- fine-tuning jobs
- local adapter runtime

本次研读没有执行测试。当前完成情况来自源码、README、架构文档、ADR、计划文档和测试用例的静态阅读。

## 推荐下一步

优先级较高的后续切片：

1. 在当前 dirty worktree 上跑通完整 backend integration suite 和 web build。
2. 测试稳定后，再把 memory 内部拆成更小的 services。
3. 在继续改 retrieval 前补长期记忆 benchmark / regression scripts。
4. 增加 exact / full-text memory search 和更清晰的 memory trace。
5. 强化模型 provider health check、fallback 和 route policy。
6. 在真实 GPU 环境验证 local training，并补质量对比工作流。
7. 扩展 memory governance：rollback、merge、privacy tier、sensitivity controls。
8. Feishu 稳定后再扩展更多 connector。

## 运行假设

主要本地开发目标是 Windows + PowerShell + Docker Desktop。

API 在本地/测试中可以使用 SQLite，但完整本地基础设施包括 PostgreSQL、Redis 和 Qdrant。

Mock 路径是开发体验的一部分。除非任务明确要求移除，否则要保持 mock provider、mock fine-tune 和 local adapter mock runtime 可用。

面向用户的项目文档目前中英混合，README 和计划文档以中文为主，后续文档可继续中文优先。
