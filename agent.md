# Agent 协作手册

最后研读日期：2026-04-28

## 工作约定

当前仓库是一个已有大量未提交改动的工作区。后续 agent 必须把现有修改视为用户或前序 agent 的工作成果，不要回滚、重排、格式化或清理无关文件，除非用户明确要求。

项目文档和源码里有中文内容。Windows PowerShell 默认读取可能出现乱码，查看 README、架构文档、计划文档时优先使用：

```powershell
Get-Content -Encoding UTF8 README.md
```

变更应保持窄范围、可验证。Laiver 已经不是一次性 Demo，而是一个本地核心链路可跑通的 MVP+ 原型；不要用大重写破坏已有闭环。

## 项目定位

当前文档里的产品名是 **Laiver**。

Laiver 是一个面向个人长期陪伴场景的 personalized AI agent / AI companion 平台原型。它的目标不是做聊天壳，而是把真实聊天记录、Persona、长期记忆、模型、训练、Skill 和外部连接器串成一条本地可运行的个人 Agent 工作流。

核心闭环是：

1. 导入聊天记录。
2. 标准化消息。
3. 抽取目标 speaker 的 Persona。
4. 写入和召回长期记忆。
5. 通过模型 provider 生成回复。
6. 调用内置或社区 Skill。
7. 接入 Feishu 等外部渠道。
8. 可选生成 LoRA / QLoRA 本地训练数据并注册 Local Adapter。

当前阶段是 **MVP+ / early alpha**。本地核心链路已经存在，但生产稳定性、效果评估、治理能力、UI polish 和更多连接器仍未完成。

## 仓库结构

```text
apps/
  api/        FastAPI 后端、SQLAlchemy 模型、Alembic 迁移、服务层、集成测试
  web/        Next.js App Router 仪表盘
packages/
  shared/     前后端共享 TypeScript 类型
docs/
  adrs/       架构决策记录
  plans/      实施计划与进度记录
scripts/
  windows/    Windows-first 本地运维脚本
  local_finetune/
```

技术栈：

- 前端：Next.js、React、TypeScript、Tailwind。
- 后端：FastAPI、Pydantic、SQLAlchemy、Alembic。
- 存储：PostgreSQL、Redis、Qdrant；测试里可走 SQLite。
- 模型：DeepSeek、OpenAI-compatible API、Ollama、Local Adapter。
- 本地运维：PowerShell 脚本 + Docker Desktop。

## 当前已实现能力

根据 README、ADR、计划文档、API 路由、共享类型和集成测试，当前仓库已经具备：

- `txt` / `csv` / `json` / WeFlow-like 微信 `xlsx` 导入预览与提交。
- normalized message 标准化、参与者识别、自己/对方/系统消息识别。
- Persona 抽取，并支持指定 `source_speaker`。
- Agent 对话编排：Persona、上下文、记忆召回、模型路由、Skill 调用、调试 trace。
- 模型 provider 注册：DeepSeek、OpenAI-compatible、Ollama、Local Adapter。
- 本地 fine-tune job：创建、dataset preview/export、mock/local launch、artifact 注册、Local Adapter runtime warm/evict。
- 内置 Skill 与受控社区 Skill 安装：manifest 或 zip。
- Feishu Connector MVP：webhook 校验、conversation mapping、delivery log、mock/live 模式、幂等处理。
- Memory V2 核心结构：`memory_episode`、`memory_fact`、`memory_revision`、`user_profile`、`relationship_state`、`memory_candidate`。
- Memory review queue：候选记忆 approve / reject。
- gated memory write：低置信、敏感或要求审核的事实先进入候选队列。
- memory maintenance：衰减、归档弱事实、忽略长期未审核 candidate、重建 profile snapshot。
- Web 页面：onboarding、imports、persona、chat、memories、skills、connectors、settings、training。

## 重要未完成项

不要把项目描述成生产就绪。当前仍需继续完成：

- 更多微信导出格式支持。
- 大文件异步导入和断点续传。
- 真实 GPU 训练稳定性、资源占用和质量验证。
- fine-tune 效果评估和 A/B 对比。
- 模型 health check、fallback 和更完整的路由策略。
- memory rollback、merge、privacy tier 和更深的治理操作。
- full-text memory search 与长期记忆 benchmark harness。
- Skill marketplace、版本更新、签名校验、权限审核和沙箱执行。
- Feishu 之外的连接器。
- 产品级 UI polish 和新手引导细节。

## 常用命令

从仓库根目录执行：

```powershell
npm.cmd run windows:doctor
npm.cmd run windows:infra:up
npm.cmd run windows:db:migrate
npm.cmd run windows:dev:api
npm.cmd run windows:dev:web
npm.cmd run build:web
python -m unittest discover -s apps/api/tests -p "test_*.py"
python scripts/run_mvp_regression.py
```

前端单独验证：

```powershell
npm.cmd run typecheck:web
npm.cmd run build:web
```

后端集成测试会在 `.tmp/test-runs` 下创建临时 SQLite 数据库和训练产物目录。

## 后续 Agent 实施原则

改后端行为前，先读 `apps/api/tests/test_integration.py`。这份测试是当前 MVP 闭环最清晰的可执行规格。

改 API shape 时，通常要同时维护：

- `apps/api/app/schemas`
- `apps/web/lib/api.ts`
- `packages/shared/src/types.ts`

改 memory 行为时，保留旧 `Memory` 表兼容路径，同时继续使用 V2 的 episode / fact / revision / profile / candidate 结构。当前迁移策略是增量 dual-write，不是硬切换。

改模型能力时，必须保留 mock 和本地开发路径。测试依赖 mock provider、mock fine-tune、Local Adapter mock runtime 等可重复路径。

改 connector 行为时，保留 Feishu webhook token 校验、delivery log、conversation mapping 和幂等处理。

改前端时，把它当作操作型 dashboard，而不是营销 landing page。首屏和页面重点应服务导入、配置、调试和运行工作流。

## 优先阅读材料

- `README.md`
- `docs/architecture.md`
- `docs/adrs/0001-mvp-foundation.md`
- `docs/adrs/0006-companion-memory-v2.md`
- `docs/plans/2026-04-04-windows-first-operations.md`
- `docs/plans/2026-04-23-laiver-memory-system-implementation-plan.md`
- `apps/api/tests/test_integration.py`
