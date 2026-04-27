# Laiver 用户使用指南

Laiver 是一个面向个人长期陪伴场景的 personalized AI agent / AI companion 原型。它的目标不是只做一个聊天壳，而是把聊天记录导入、Persona 生成、长期记忆、本地/云端模型、微调训练和社区 Skill 连接成一条可使用的工作流。

当前项目处于 **MVP+ / early alpha** 阶段：核心链路已经能本地跑通，适合继续打磨成完整产品。

## 你可以用它做什么

### 一键 Onboarding

推荐新用户从这里开始：

- 页面地址：`/onboarding`
- 本地访问：<http://localhost:3000/onboarding>

Onboarding 会把主要步骤串起来：

1. 上传微信或其他聊天记录文件。
2. 预览并提交标准化消息。
3. 选择目标 speaker，生成 Persona。
4. 创建本地 QLoRA fine-tune 数据集。
5. 初始化默认模型 provider 和内置 Skills。
6. 跳转到聊天页面开始测试。

注意：训练启动需要占用本地计算资源，所以 Laiver 不会默认自动启动训练。你可以在 Onboarding 或 Training 页面手动点击启动。

### 聊天记录导入

页面地址：`/imports`

当前支持：

- `txt`
- `csv`
- `json`
- `xlsx`

其中 `xlsx` 已支持类似 WeFlow 导出的微信聊天记录格式，可以完成：

- 导入预览
- 参与者识别
- 自己 / 对方 / 系统消息识别
- 消息标准化
- 元数据保留
- 后续 Persona 和训练数据复用

### Persona 生成

页面地址：`/persona`

你可以从导入后的聊天记录中抽取某个 speaker 的表达风格，生成可编辑的 Persona。当前 Persona 包含：

- 语气
- 详细程度
- 常见表达
- 常见话题
- 回复风格
- 关系风格
- 证据片段

对于微信双人聊天，建议明确选择目标 speaker，避免把自己和对方的风格混在一起。

### 本地微调训练

页面地址：`/training`

当前支持从已导入的聊天记录生成本地训练任务：

- 创建 fine-tune job
- 预览训练样本
- 生成本地 LoRA / QLoRA 数据集
- 启动本地训练
- 将完成后的 adapter 注册为模型 provider
- 设置注册后的 provider 为默认模型

当前训练链路已经具备基础闭环，但仍建议在真实 GPU 环境下继续验证训练稳定性、显存占用和效果评估。

### 模型接入

页面地址：`/settings`

当前支持：

- DeepSeek
- OpenAI-compatible API
- Ollama
- Local Adapter

Local Adapter 已支持常驻推理服务，可以用于本地模型或微调 adapter 的推理接入。

### 聊天与调试

页面地址：`/chat`

聊天页面可以测试：

- Persona 是否参与回复
- Memory 是否被召回
- Skill 是否被触发
- 当前使用的模型 provider
- 长对话摘要是否生效
- memory query route
- 写入了哪些新记忆

### 长期记忆系统

页面地址：`/memories`

Laiver 的 memory 系统已经不只是简单笔记。目前已经支持：

- instruction / preference / episodic / session 分类
- duplicate reinforcement
- conflict supersede
- episode ledger
- memory fact
- memory revision
- user profile snapshot
- relationship state snapshot
- candidate review queue
- gated write：低置信、敏感或要求审核的记忆先进入候选队列
- memory consolidation / decay 后台维护
- 手动运行维护任务

在 Memory 页面里，你可以看到：

- 最近写入的 memory
- episode ledger
- fact ledger
- revision history
- review queue
- conflict groups
- structured profile / relationship snapshot

也可以点击 `Run Maintenance` 手动执行记忆维护。维护任务会做：

- 按 `decay_policy` 衰减长期事实
- 归档弱化到阈值以下的 fact
- 忽略长期未审核的 candidate
- 重建 user profile 和 relationship state

### Skill 系统

页面地址：`/skills`

当前支持：

- 内置 Skill
- 社区 Skill 包上传安装
- 启用 / 停用 / 删除 Skill
- 查看 manifest
- 查看调用日志

社区 Skill 当前是安全受控版：

- 支持上传 `skill.json`
- 支持上传包含 `skill.json` 的 `.zip`
- 可以复用平台允许的本地 handler
- 暂不支持无沙箱执行任意第三方代码

后续目标是补齐远程 marketplace、版本更新、签名校验、权限审核和沙箱执行。

### 连接器

页面地址：`/connectors`

当前已有 Feishu Connector MVP，用于验证：

- webhook 入站消息
- conversation mapping
- Agent 回复出站
- mock / live 模式切换

这块可以作为后续接微信、Telegram、邮件等渠道的模板。

## 快速开始

### 1. 准备环境变量

```powershell
copy .env.example .env
```

### 2. 启动基础设施

```powershell
npm.cmd run windows:infra:up
```

### 3. 执行数据库迁移

```powershell
npm.cmd run windows:db:migrate
```

### 4. 启动后端

```powershell
npm.cmd run windows:dev:api
```

### 5. 启动前端

```powershell
npm.cmd run windows:dev:web
```

### 6. 打开页面

- Web: <http://localhost:3000>
- Onboarding: <http://localhost:3000/onboarding>
- API Docs: <http://localhost:8000/docs>

## 推荐体验路径

第一次使用建议直接走：

1. 打开 `/onboarding`
2. 上传微信聊天记录 `xlsx`
3. 预览并保存 import
4. 抽取目标 speaker 的 Persona
5. 创建本地训练数据集
6. 初始化模型和 Skills
7. 打开 `/chat` 测试回复
8. 打开 `/memories` 查看写入、召回、候选审核和维护结果

如果你想分模块调试，也可以按页面分别进入：

- `/imports`：单独测试导入
- `/persona`：单独抽取和编辑 Persona
- `/training`：单独创建和启动训练任务
- `/settings`：配置模型 provider
- `/skills`：安装和管理 Skill
- `/memories`：调试长期记忆
- `/chat`：进行对话验证

## 常用命令

```powershell
npm.cmd run windows:doctor
npm.cmd run windows:infra:up
npm.cmd run windows:infra:down
npm.cmd run windows:db:migrate
npm.cmd run windows:dev:api
npm.cmd run windows:dev:web
npm.cmd run build:web
python -m unittest discover -s apps/api/tests -p "test_*.py"
python scripts/run_mvp_regression.py
```

## 当前完成度

已经具备可用基础：

- 微信聊天记录 `xlsx` 导入
- normalized message 标准化
- Persona 抽取
- 本地 fine-tune job 和 dataset preview
- 外部 API / Ollama / Local Adapter 模型接入
- 社区 Skill 本地安装
- 长期 memory v2 核心结构
- candidate review queue
- memory decay / consolidation 维护任务
- 一键 Onboarding 页面

仍需继续完善：

- 更多微信导出格式支持
- 大文件异步导入和断点续传
- 真实 GPU 训练稳定性验证
- 训练效果评估和 A/B 对比
- 模型 fallback / health check / 路由策略
- memory rollback / merge / privacy tier
- Skill marketplace、签名校验和沙箱执行
- 产品级 UI polish 和新手引导细节

## 项目定位

Laiver 现在已经不是空壳 Demo，而是一个可以本地跑通核心闭环的 personalized agent 平台原型。它已经能导入聊天记录、生成 Persona、构建训练数据、接入模型、保留长期记忆、管理 Skills，并通过 Onboarding 把这些能力串成一条用户路径。

