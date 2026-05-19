export type Language = "en" | "zh";

type Translation = {
  en: string;
  zh: string;
};

export const translations: Record<string, Translation> = {
  Dashboard: { en: "Dashboard", zh: "总览" },
  Initialization: { en: "Initialization", zh: "初始化" },
  "Dialog // 02": { en: "Dialog // 02", zh: "对话 // 02" },
  Imports: { en: "Imports", zh: "导入" },
  Persona: { en: "Persona", zh: "人格画像" },
  "Pilot Training": { en: "Pilot Training", zh: "模型训练" },
  "Memory Bank": { en: "Memory Bank", zh: "记忆库" },
  Equipment: { en: "Equipment", zh: "技能装备" },
  Connectors: { en: "Connectors", zh: "连接器" },
  "Mission Control": { en: "Mission Control", zh: "任务控制台" },
  "SYSTEM ONLINE": { en: "SYSTEM ONLINE", zh: "系统在线" },
  "PILOT // 02": { en: "PILOT // 02", zh: "驾驶员 // 02" },
  "SYNC RATIO": { en: "SYNC RATIO", zh: "同步率" },
  STABLE: { en: "STABLE", zh: "稳定" },
  NIGHT: { en: "NIGHT", zh: "夜间" },
  DAY: { en: "DAY", zh: "日间" },
  "NERV TERMINAL · TOKYO-3": { en: "NERV TERMINAL · TOKYO-3", zh: "NERV 终端 · 第三新东京市" },

  // Splash intro
  "INITIATING NERV TERMINAL": { en: "INITIATING NERV TERMINAL", zh: "初始化 NERV 终端" },
  "AT FIELD · ACTIVATED": { en: "AT FIELD · ACTIVATED", zh: "AT 力场 · 已激活" },
  SKIP: { en: "SKIP", zh: "跳过" },

  "MISSION 00 / DASHBOARD": { en: "MISSION 00 / DASHBOARD", zh: "任务 00 / 总览" },
  "MAGI 一期验收终端": { en: "MAGI Phase-1 Validation Terminal", zh: "MAGI 一期验收终端" },
  "当前阶段只做一件事：把导入、Persona、Memory、Agent 主链路打磨扎实，并可稳定复现实验。": {
    en: "Current focus: make the import, Persona, Memory, and Agent loop stable and repeatable.",
    zh: "当前阶段只做一件事：把导入、Persona、Memory、Agent 主链路打磨扎实，并可稳定复现实验。"
  },
  "8-STEP E2E": { en: "8-STEP E2E", zh: "8 步端到端" },
  "▶ SYNCHRONIZATION COMPLETE": { en: "▶ SYNCHRONIZATION COMPLETE", zh: "▶ 同步完成" },
  "PERSONAL AGENT // MAGI v0.1": { en: "PERSONAL AGENT // MAGI v0.1", zh: "个人 Agent // MAGI v0.1" },
  "All systems nominal. Verify import → persona → memory → agent loop before expanding mission scope.": {
    en: "All systems nominal. Verify import → persona → memory → agent loop before expanding mission scope.",
    zh: "系统状态正常。扩展任务范围前，请先验收导入 → Persona → 记忆 → Agent 主链路。"
  },
  "AT FIELD STABLE": { en: "AT FIELD STABLE", zh: "AT 力场稳定" },
  "MAGI ONLINE": { en: "MAGI ONLINE", zh: "MAGI 在线" },
  "SYNC RATIO 87.4%": { en: "SYNC RATIO 87.4%", zh: "同步率 87.4%" },
  验收步骤: { en: "Validation Steps", zh: "验收步骤" },
  "按顺序验证上传、解析、入库、抽取、对话、写入、召回。": {
    en: "Verify upload, parsing, commit, extraction, chat, write, and recall in order.",
    zh: "按顺序验证上传、解析、入库、抽取、对话、写入、召回。"
  },
  核心页面: { en: "Core Pages", zh: "核心页面" },
  "导入、Persona、聊天、Memory 四个页面可直接验收。": {
    en: "Imports, Persona, Chat, and Memory can be validated directly.",
    zh: "导入、Persona、聊天、Memory 四个页面可直接验收。"
  },
  默认数据库: { en: "Default Database", zh: "默认数据库" },
  "本地启动后自动建表，无需单独起数据库进程。": {
    en: "Local startup creates tables automatically; no separate database process is required.",
    zh: "本地启动后自动建表，无需单独起数据库进程。"
  },
  当前模型: { en: "Current Model", zh: "当前模型" },
  "无 API Key 时走本地 mock fallback，便于链路联调。": {
    en: "Without an API key, local mock fallback keeps the workflow testable.",
    zh: "无 API Key 时走本地 mock fallback，便于链路联调。"
  },
  导入链路: { en: "Import Flow", zh: "导入链路" },
  "上传聊天记录，查看 normalized message 预览，再提交入库。": {
    en: "Upload a chat archive, inspect normalized messages, then commit it.",
    zh: "上传聊天记录，查看 normalized message 预览，再提交入库。"
  },
  "Persona 链路": { en: "Persona Flow", zh: "Persona 链路" },
  "从导入数据抽取 Persona，并检查 tone、topics、phrases 和 style。": {
    en: "Extract a Persona from imported data and inspect tone, topics, phrases, and style.",
    zh: "从导入数据抽取 Persona，并检查 tone、topics、phrases 和 style。"
  },
  对话链路: { en: "Chat Flow", zh: "对话链路" },
  "选择 Persona 发起对话，查看 Agent 响应、命中的 memory 和写入结果。": {
    en: "Pick a Persona, start a chat, then inspect the Agent response, memory hits, and writes.",
    zh: "选择 Persona 发起对话，查看 Agent 响应、命中的 memory 和写入结果。"
  },
  验收闭环: { en: "Validation Loop", zh: "验收闭环" },
  "在 Memory 页面确认最近写入记录，并对下一轮对话做 recall 验证。": {
    en: "Confirm recent writes in Memory and validate recall in the next turn.",
    zh: "在 Memory 页面确认最近写入记录，并对下一轮对话做 recall 验证。"
  },

  "Conversation Quality": { en: "Conversation Quality", zh: "对话质量" },
  "Chat Flow Validation": { en: "Chat Flow Validation", zh: "对话链路验证" },
  "Tune persona, skills, and memory write controls at the conversation level, then inspect exactly which memories, persona fields, and skill outputs shaped the answer.": {
    en: "Tune persona, skills, and memory write controls at the conversation level, then inspect exactly which memories, persona fields, and skill outputs shaped the answer.",
    zh: "在会话层调整 Persona、技能和记忆写入开关，并检查哪些记忆、Persona 字段和技能输出影响了回答。"
  },
  "Controls + Explanation": { en: "Controls + Explanation", zh: "控制项 + 解释" },
  "Conversation Controls": { en: "Conversation Controls", zh: "会话控制" },
  "Set persona, provider, and runtime switches before sending the next turn.": {
    en: "Set persona, provider, and runtime switches before sending the next turn.",
    zh: "发送下一轮前，先设置 Persona、模型供应商和运行开关。"
  },
  "Current Persona": { en: "Current Persona", zh: "当前 Persona" },
  "Model Provider": { en: "Model Provider", zh: "模型供应商" },
  Skills: { en: "Skills", zh: "技能" },
  "Planner + tool execution for the next turns.": {
    en: "Planner + tool execution for the next turns.",
    zh: "允许后续对话使用规划器和工具执行。"
  },
  "Memory Write": { en: "Memory Write", zh: "记忆写入" },
  "Store new memories after this turn.": {
    en: "Store new memories after this turn.",
    zh: "本轮结束后写入新的长期记忆。"
  },
  "New Conversation": { en: "New Conversation", zh: "新建会话" },
  "Debug Panel": { en: "Debug Panel", zh: "调试面板" },
  "Runtime Controls": { en: "Runtime Controls", zh: "运行控制" },
  "Provider + Model": { en: "Provider + Model", zh: "供应商 + 模型" },
  "Compression Status": { en: "Compression Status", zh: "压缩状态" },
  "Skills Used": { en: "Skills Used", zh: "已调用技能" },
  "Memories Used In Answer": { en: "Memories Used In Answer", zh: "回答引用的记忆" },
  "Persona Fields Used": { en: "Persona Fields Used", zh: "使用的 Persona 字段" },
  "Skill Outputs Referenced": { en: "Skill Outputs Referenced", zh: "引用的技能输出" },
  "Skill Invocation Details": { en: "Skill Invocation Details", zh: "技能调用详情" },
  "Memory Hits": { en: "Memory Hits", zh: "命中的记忆" },
  "Memory Writes": { en: "Memory Writes", zh: "写入的记忆" },

  "Step 1-3": { en: "Step 1-3", zh: "第 1-3 步" },
  "Import, Preview, and Commit": { en: "Import, Preview, and Commit", zh: "导入、预览与保存" },
  "Upload chat history, verify normalized messages, inspect source metadata, and then save the import for downstream Persona work.": {
    en: "Upload chat history, verify normalized messages, inspect source metadata, and then save the import for downstream Persona work.",
    zh: "上传聊天记录，确认标准化消息和来源元数据，再保存给后续 Persona 链路使用。"
  },
  "Import -> Preview -> Commit": { en: "Import -> Preview -> Commit", zh: "导入 -> 预览 -> 保存" },
  "Upload Source File": { en: "Upload Source File", zh: "上传源文件" },
  "Supports plain text, CSV, JSON, and WeFlow-style WeChat XLSX exports.": {
    en: "Supports plain text, CSV, JSON, and WeFlow-style WeChat XLSX exports.",
    zh: "支持纯文本、CSV、JSON，以及类似 WeFlow 的微信 XLSX 导出。"
  },
  "Normalized Message Preview": { en: "Normalized Message Preview", zh: "标准化消息预览" },
  "Committed Imports": { en: "Committed Imports", zh: "已保存导入" },

  Quality: { en: "Quality", zh: "质量" },
  "Persona Validation": { en: "Persona Validation", zh: "Persona 验证" },
  "Evidence + Preview": { en: "Evidence + Preview", zh: "证据 + 预览" },
  "Extract Persona": { en: "Extract Persona", zh: "抽取 Persona" },
  "Import Source": { en: "Import Source", zh: "导入来源" },
  "Target Speaker": { en: "Target Speaker", zh: "目标发言人" },
  "Speaker Summary": { en: "Speaker Summary", zh: "发言人摘要" },
  "Extraction Details": { en: "Extraction Details", zh: "抽取详情" },
  "Edit Persona": { en: "Edit Persona", zh: "编辑 Persona" },
  "Answer Preview / Compare": { en: "Answer Preview / Compare", zh: "回答预览 / 对比" },

  "Memory Validation": { en: "Memory Validation", zh: "记忆链路验证" },
  "Profile + Conflict": { en: "Profile + Conflict", zh: "画像 + 冲突处理" },
  "Memory Flow": { en: "Memory Flow", zh: "记忆流转" },
  "Write and Search": { en: "Write and Search", zh: "写入与检索" },
  "Memory Type": { en: "Memory Type", zh: "记忆类型" },
  "New Memory": { en: "New Memory", zh: "新记忆" },
  "Recall Query": { en: "Recall Query", zh: "召回查询" },
  "Filters and States": { en: "Filters and States", zh: "筛选与状态" },
  "Long-Term Profile": { en: "Long-Term Profile", zh: "长期画像" },
  "Structured Snapshots": { en: "Structured Snapshots", zh: "结构化快照" },
  "Recent Writes": { en: "Recent Writes", zh: "最近写入" },
  "Episode Ledger": { en: "Episode Ledger", zh: "事件账本" },
  "Fact Ledger": { en: "Fact Ledger", zh: "事实账本" },
  "Revision History": { en: "Revision History", zh: "修订历史" },
  "Review Queue": { en: "Review Queue", zh: "审核队列" },
  "Conflict Groups": { en: "Conflict Groups", zh: "冲突组" },
  "Potential Duplicates": { en: "Potential Duplicates", zh: "潜在重复" },
  "Memory Table": { en: "Memory Table", zh: "记忆表" },

  "System Settings": { en: "System Settings", zh: "系统设置" },
  "Model Providers": { en: "Model Providers", zh: "模型供应商" },
  "External + Local": { en: "External + Local", zh: "云端 + 本地" },
  "Provider Registry": { en: "Provider Registry", zh: "供应商列表" },
  "Model Switcher": { en: "Model Switcher", zh: "模型切换器" },
  "Add Provider": { en: "Add Provider", zh: "添加供应商" },
  "Provider Type": { en: "Provider Type", zh: "供应商类型" },
  Name: { en: "Name", zh: "名称" },
  "Base URL": { en: "Base URL", zh: "基础地址" },
  "Model Name": { en: "Model Name", zh: "模型名称" },
  "API Key Ref": { en: "API Key Ref", zh: "API Key 引用" },
  "Validation Result": { en: "Validation Result", zh: "验证结果" },
  "Resident Runtime": { en: "Resident Runtime", zh: "常驻运行时" },

  "Local Fine-Tuning": { en: "Local Fine-Tuning", zh: "本地微调" },
  "Training Jobs": { en: "Training Jobs", zh: "训练任务" },
  "Dataset + Model": { en: "Dataset + Model", zh: "数据集 + 模型" },
  "Training Flow": { en: "Training Flow", zh: "训练流程" },
  "Create Job": { en: "Create Job", zh: "创建任务" },
  "Source Import": { en: "Source Import", zh: "导入来源" },
  "Training Backend": { en: "Training Backend", zh: "训练后端" },
  "Base Model": { en: "Base Model", zh: "基础模型" },
  "Context Window": { en: "Context Window", zh: "上下文窗口" },
  Jobs: { en: "Jobs", zh: "任务列表" },
  "Job Detail": { en: "Job Detail", zh: "任务详情" },
  "Dataset Preview": { en: "Dataset Preview", zh: "数据集预览" },

  "Skill Runtime": { en: "Skill Runtime", zh: "技能运行时" },
  "Skill Registry": { en: "Skill Registry", zh: "技能注册表" },
  "Builtin + Community": { en: "Builtin + Community", zh: "内置 + 社区" },
  "Registered Skills": { en: "Registered Skills", zh: "已注册技能" },
  "Install Community Skill": { en: "Install Community Skill", zh: "安装社区技能" },
  "Skill Detail": { en: "Skill Detail", zh: "技能详情" },
  "Recent Invocations": { en: "Recent Invocations", zh: "最近调用" },

  "Connector Layer": { en: "Connector Layer", zh: "连接器层" },
  "Feishu Connector": { en: "Feishu Connector", zh: "飞书连接器" },
  "Receive + Reply": { en: "Receive + Reply", zh: "接收 + 回复" },
  "Create Connector": { en: "Create Connector", zh: "创建连接器" },
  "Connector Details": { en: "Connector Details", zh: "连接器详情" },
  "Conversation Mapping": { en: "Conversation Mapping", zh: "会话映射" },
  "Trace Snapshot": { en: "Trace Snapshot", zh: "链路快照" },
  "Recent Deliveries": { en: "Recent Deliveries", zh: "最近投递" },
  "Delivery Failures": { en: "Delivery Failures", zh: "投递失败" },

  Refresh: { en: "Refresh", zh: "刷新" },
  Search: { en: "Search", zh: "搜索" },
  Validate: { en: "Validate", zh: "验证" },
  "Validate Selected": { en: "Validate Selected", zh: "验证所选" },
  "Set Default": { en: "Set Default", zh: "设为默认" },
  Disable: { en: "Disable", zh: "停用" },
  Enable: { en: "Enable", zh: "启用" },
  Warm: { en: "Warm", zh: "预热" },
  Evict: { en: "Evict", zh: "释放" },
  Check: { en: "Check", zh: "检查" },
  Use: { en: "Use", zh: "使用" },
  Launch: { en: "Launch", zh: "启动" },
  Register: { en: "Register", zh: "注册" },
  "Create Provider": { en: "Create Provider", zh: "创建供应商" },
  "Create Fine-Tune Job": { en: "Create Fine-Tune Job", zh: "创建微调任务" },
  "Launch Local Training": { en: "Launch Local Training", zh: "启动本地训练" },
  "Store Memory": { en: "Store Memory", zh: "保存记忆" },
  "Run Maintenance": { en: "Run Maintenance", zh: "运行维护" },
  "Sync Builtins": { en: "Sync Builtins", zh: "同步内置技能" },
  "Install Package": { en: "Install Package", zh: "安装包" },
  "Save Config": { en: "Save Config", zh: "保存配置" },
  "Test Connector": { en: "Test Connector", zh: "测试连接器" },

  current: { en: "current", zh: "当前" },
  default: { en: "default", zh: "默认" },
  enabled: { en: "enabled", zh: "已启用" },
  disabled: { en: "disabled", zh: "已停用" },
  active: { en: "active", zh: "活跃" },
  archived: { en: "archived", zh: "已归档" },
  ignored: { en: "ignored", zh: "已忽略" },
  pinned: { en: "pinned", zh: "已置顶" },
  pending: { en: "pending", zh: "待处理" },
  completed: { en: "completed", zh: "已完成" },
  running: { en: "running", zh: "运行中" },
  failed: { en: "failed", zh: "失败" },
  ok: { en: "ok", zh: "正常" },
  mock: { en: "mock", zh: "模拟" },
  live: { en: "live", zh: "真实" },
  webhook: { en: "webhook", zh: "Webhook" },
  openapi: { en: "openapi", zh: "OpenAPI" },
  available: { en: "available", zh: "可用" },
  unavailable: { en: "unavailable", zh: "不可用" },
  healthy: { en: "healthy", zh: "健康" },
  unhealthy: { en: "unhealthy", zh: "异常" },
  session: { en: "session", zh: "会话" },
  episodic: { en: "episodic", zh: "事件" },
  semantic: { en: "semantic", zh: "语义" },
  instruction: { en: "instruction", zh: "指令" },
  all: { en: "all", zh: "全部" },
  self: { en: "self", zh: "本人" },
  messages: { en: "messages", zh: "条消息" },
  importance: { en: "importance", zh: "重要度" },
  confidence: { en: "confidence", zh: "置信度" },
  Type: { en: "Type", zh: "类型" },
  Label: { en: "Label", zh: "标签" },
  Content: { en: "Content", zh: "内容" },
  Score: { en: "Score", zh: "分数" },
  Source: { en: "Source", zh: "来源" },
  State: { en: "State", zh: "状态" },
  Actions: { en: "Actions", zh: "操作" },
  Speaker: { en: "Speaker", zh: "发言人" },
  Role: { en: "Role", zh: "角色" },
  Dataset: { en: "Dataset", zh: "数据集" },
  Config: { en: "Config", zh: "配置" },
  Output: { en: "Output", zh: "输出" },
  Split: { en: "Split", zh: "拆分" },
  "Last Error": { en: "Last Error", zh: "最近错误" },
  Manifest: { en: "Manifest", zh: "清单" },
  "Toggle theme": { en: "Toggle theme", zh: "切换明暗主题" },
  "SYNCHRONIZATION COMPLETE": { en: "SYNCHRONIZATION COMPLETE", zh: "同步完成" },
  "STAGE 01": { en: "STAGE 01", zh: "阶段 01" },
  "STAGE 02": { en: "STAGE 02", zh: "阶段 02" },
  "STAGE 03": { en: "STAGE 03", zh: "阶段 03" },
  "STAGE 04": { en: "STAGE 04", zh: "阶段 04" },
  Auto: { en: "Auto", zh: "自动" },
  On: { en: "On", zh: "开" },
  Off: { en: "Off", zh: "关" },
  YES: { en: "YES", zh: "是" },
  NO: { en: "NO", zh: "否" },
  none: { en: "none", zh: "无" },
  ready: { en: "ready", zh: "就绪" },
  empty: { en: "empty", zh: "空" },
  done: { en: "done", zh: "完成" },
  cold: { en: "cold", zh: "冷启动" },
  resident: { en: "resident", zh: "常驻" },
  completion: { en: "completion", zh: "补全" },
  stream: { en: "stream", zh: "流式" },
  tool: { en: "tool", zh: "工具" },
  "No items.": { en: "No items.", zh: "暂无项目。" },
  "No values.": { en: "No values.", zh: "暂无数值。" },
  "No run yet.": { en: "No run yet.", zh: "还没有运行记录。" },
  "No description": { en: "No description", zh: "暂无描述" },
  "No Persona": { en: "No Persona", zh: "不使用人格画像" },
  "No Persona selected.": { en: "No Persona selected.", zh: "尚未选择人格画像。" },
  "No Persona records yet.": { en: "No Persona records yet.", zh: "暂无人格画像记录。" },
  "No conversations yet.": { en: "No conversations yet.", zh: "暂无会话。" },
  "No imports committed yet.": { en: "No imports committed yet.", zh: "暂无已保存的导入。" },
  "No invocation records yet.": { en: "No invocation records yet.", zh: "暂无调用记录。" },
  "No training jobs yet.": { en: "No training jobs yet.", zh: "暂无训练任务。" },
  "No training job selected yet.": { en: "No training job selected yet.", zh: "尚未选择训练任务。" },
  "No delivery records yet.": { en: "No delivery records yet.", zh: "暂无投递记录。" },
  "No conversation mappings yet.": { en: "No conversation mappings yet.", zh: "暂无会话映射。" },
  "No skills used in the last run.": { en: "No skills used in the last run.", zh: "上次运行未调用技能。" },
  "No summary injected for the last run.": { en: "No summary injected for the last run.", zh: "上次运行未注入摘要。" },
  "No persona fields were applied.": { en: "No persona fields were applied.", zh: "没有应用人格画像字段。" },
  "No grounded skill output was referenced.": { en: "No grounded skill output was referenced.", zh: "没有引用已落地的技能输出。" },
  "No invocation details for the last run.": { en: "No invocation details for the last run.", zh: "上次运行没有调用详情。" },
  "No completion content returned.": { en: "No completion content returned.", zh: "未返回补全文本。" },
  "No stream content returned.": { en: "No stream content returned.", zh: "未返回流式文本。" },
  "No default provider": { en: "No default provider", zh: "暂无默认供应商" },
  "Create or bootstrap a provider before switching.": {
    en: "Create or bootstrap a provider before switching.",
    zh: "切换前请先创建或初始化一个模型供应商。"
  },
  "Send the first message to create a new conversation.": {
    en: "Send the first message to create a new conversation.",
    zh: "发送第一条消息来创建新会话。"
  },
  "Try toggling skills or memory write, or switch persona, then send the same prompt again to compare the result.": {
    en: "Try toggling skills or memory write, or switch persona, then send the same prompt again to compare the result.",
    zh: "可以切换技能、记忆写入或人格画像，然后再次发送同一条提示词来对比结果。"
  },
  "This panel is rendered from the Chat feature view model, not raw backend debug fields.": {
    en: "This panel is rendered from the Chat feature view model, not raw backend debug fields.",
    zh: "这个面板来自 Chat 功能的视图模型，不直接展示后端原始调试字段。"
  },
  "Type a message for conversation quality testing...": {
    en: "Type a message for conversation quality testing...",
    zh: "输入一条用于测试对话质量的消息..."
  },
  "Start New Conversation": { en: "Start New Conversation", zh: "新建会话" },
  "Send Message": { en: "Send Message", zh: "发送消息" },
  "Long-Horizon Summary": { en: "Long-Horizon Summary", zh: "长程摘要" },
  "persona selected": { en: "persona selected", zh: "已选择人格画像" },
  "no persona": { en: "no persona", zh: "无人格画像" },
  "skills on": { en: "skills on", zh: "技能已开启" },
  "skills off": { en: "skills off", zh: "技能已关闭" },
  "memory write on": { en: "memory write on", zh: "记忆写入已开启" },
  "memory write off": { en: "memory write off", zh: "记忆写入已关闭" },
  "skills enabled": { en: "skills enabled", zh: "技能已启用" },
  "skills disabled": { en: "skills disabled", zh: "技能已停用" },
  "memory write enabled": { en: "memory write enabled", zh: "记忆写入已启用" },
  "memory write disabled": { en: "memory write disabled", zh: "记忆写入已停用" },
  "memory written": { en: "memory written", zh: "已写入记忆" },
  "no memory write": { en: "no memory write", zh: "未写入记忆" },
  explicit: { en: "explicit", zh: "显式指定" },
  "default route": { en: "default route", zh: "默认路由" },
  "no provider": { en: "no provider", zh: "无供应商" },
  "compression active": { en: "compression active", zh: "压缩已启用" },
  "full short history": { en: "full short history", zh: "完整短历史" },
  "Default provider": { en: "Default provider", zh: "默认供应商" },
  "Choose a txt / csv / json / xlsx file": {
    en: "Choose a txt / csv / json / xlsx file",
    zh: "选择 txt / csv / json / xlsx 文件"
  },
  "Parse first, inspect the result, then commit it into the import registry.": {
    en: "Parse first, inspect the result, then commit it into the import registry.",
    zh: "先解析并检查结果，再保存到导入记录中。"
  },
  "Commit Import": { en: "Commit Import", zh: "保存导入" },
  "After you upload a file, the normalized rows will appear here.": {
    en: "After you upload a file, the normalized rows will appear here.",
    zh: "上传文件后，标准化后的消息行会显示在这里。"
  },
  "Confirm speaker, role, and content before the data enters the shared import registry.": {
    en: "Confirm speaker, role, and content before the data enters the shared import registry.",
    zh: "数据进入导入记录前，请先确认发言人、角色和内容。"
  },
  "Saved imports stay available here for Persona extraction and later inspection.": {
    en: "Saved imports stay available here for Persona extraction and later inspection.",
    zh: "已保存的导入会保留在这里，供后续抽取 Persona 和复查使用。"
  },
  "Choose an import and optionally pick the speaker whose style you want to model.": {
    en: "Choose an import and optionally pick the speaker whose style you want to model.",
    zh: "选择一份导入记录，也可以指定想要建模的发言人。"
  },
  "Imported": { en: "Imported", zh: "已导入" },
  "Answer Preview": { en: "Answer Preview", zh: "回答预览" },
  "Before": { en: "Before", zh: "修改前" },
  "After": { en: "After", zh: "修改后" },
  "Memory created.": { en: "Memory created.", zh: "记忆已创建。" },
  "Memory search complete.": { en: "Memory search complete.", zh: "记忆搜索完成。" },
  "Capture": { en: "Capture", zh: "捕获" },
  "Conversation turn becomes a memory row.": { en: "Conversation turn becomes a memory row.", zh: "对话轮次会先成为一条记忆记录。" },
  "Episode": { en: "Episode", zh: "事件" },
  "Raw source event is preserved first.": { en: "Raw source event is preserved first.", zh: "先保留原始来源事件。" },
  "Review": { en: "Review", zh: "审核" },
  "Candidate review gate before commit.": { en: "Candidate review gate before commit.", zh: "候选记忆在提交前进入审核关口。" },
  "Fact": { en: "Fact", zh: "事实" },
  "Stable facts and revisions are tracked.": { en: "Stable facts and revisions are tracked.", zh: "稳定事实和修订记录会持续追踪。" },
  "Profile": { en: "Profile", zh: "画像" },
  "Long-term summary rebuilt from active facts.": { en: "Long-term summary rebuilt from active facts.", zh: "长期摘要会根据活跃事实重建。" },
  "Recall": { en: "Recall", zh: "召回" },
  "Vector search accelerates retrieval.": { en: "Vector search accelerates retrieval.", zh: "向量搜索用于加速检索。" },
  "Qdrant ready": { en: "Qdrant ready", zh: "Qdrant 就绪" },
  "SQL fallback": { en: "SQL fallback", zh: "SQL 备用检索" },
  "All Sources": { en: "All Sources", zh: "全部来源" },
  "Min Score": { en: "Min Score", zh: "最低分数" },
  "Show duplicate groups only": { en: "Show duplicate groups only", zh: "只显示重复分组" },
  "Create or select a job to inspect the generated dataset preview.": {
    en: "Create or select a job to inspect the generated dataset preview.",
    zh: "创建或选择任务后，可查看生成的数据集预览。"
  },
  "The dataset, local runner, provider registration, and default switch are kept in one chain.": {
    en: "The dataset, local runner, provider registration, and default switch are kept in one chain.",
    zh: "数据集、本地运行器、供应商注册和默认切换会串成一条链路。"
  },
  "Choose an imported conversation, a target speaker, and the local Qwen3-14B training mode.": {
    en: "Choose an imported conversation, a target speaker, and the local Qwen3-14B training mode.",
    zh: "选择导入的对话、目标发言人，以及本地 Qwen3-14B 训练模式。"
  },
  "Training Running": { en: "Training Running", zh: "训练运行中" },
  "Launching...": { en: "Launching...", zh: "启动中..." },
  "Registering...": { en: "Registering...", zh: "注册中..." },
  "Register Provider": { en: "Register Provider", zh: "注册供应商" },
  "Adapter Artifact": { en: "Adapter Artifact", zh: "适配器产物" },
  "Registered Provider": { en: "Registered Provider", zh: "已注册供应商" },
  "Launcher Command": { en: "Launcher Command", zh: "启动命令" },
  "The last assistant message in each sample is the target speaker response used for fine-tuning.": {
    en: "The last assistant message in each sample is the target speaker response used for fine-tuning.",
    zh: "每个样本中的最后一条 assistant 消息，就是用于微调的目标发言人回复。"
  },
  "Local builtin skills and installed community packages share one runtime registry.": {
    en: "Local builtin skills and installed community packages share one runtime registry.",
    zh: "本地内置技能和已安装的社区包共用同一个运行时注册表。"
  },
  "Import a `skill.json` package or a `.zip` archive containing `skill.json`. Add `runtime.json` when the package should proxy an approved local handler.": {
    en: "Import a `skill.json` package or a `.zip` archive containing `skill.json`. Add `runtime.json` when the package should proxy an approved local handler.",
    zh: "导入 `skill.json` 包或包含 `skill.json` 的 `.zip` 归档；需要代理已批准的本地处理器时再加入 `runtime.json`。"
  },
  "Current approved handlers: `memory-search`, `task-extractor`.": {
    en: "Current approved handlers: `memory-search`, `task-extractor`.",
    zh: "当前已批准的处理器：`memory-search`、`task-extractor`。"
  },
  "Inspect the installed manifest, runtime config, and execution mode for the selected skill.": {
    en: "Inspect the installed manifest, runtime config, and execution mode for the selected skill.",
    zh: "查看所选技能的安装清单、运行配置和执行模式。"
  },
  "Remove Community Skill": { en: "Remove Community Skill", zh: "移除社区技能" },
  "Create a connector first.": { en: "Create a connector first.", zh: "请先创建连接器。" },
  "Start with mock mode locally. When you are ready for live Feishu replies, switch the delivery mode to webhook or OpenAPI and save the connector config below.": {
    en: "Start with mock mode locally. When you are ready for live Feishu replies, switch the delivery mode to webhook or OpenAPI and save the connector config below.",
    zh: "本地先使用模拟模式。准备接入真实飞书回复时，将投递模式切换为 webhook 或 OpenAPI，并保存下面的连接器配置。"
  },
  "Webhook path:": { en: "Webhook path:", zh: "Webhook 路径：" },
  Mode: { en: "Mode", zh: "模式" },
  "Delivery Mode": { en: "Delivery Mode", zh: "投递模式" },
  "Verification Token": { en: "Verification Token", zh: "验证 Token" },
  "Reply Webhook URL": { en: "Reply Webhook URL", zh: "回复 Webhook URL" },
  "App ID": { en: "App ID", zh: "App ID" },
  "App Secret": { en: "App Secret", zh: "App Secret" },
  "Receive ID Type": { en: "Receive ID Type", zh: "接收 ID 类型" },
  "OpenAPI Base URL": { en: "OpenAPI Base URL", zh: "OpenAPI 基础地址" },
  "Force delivery failure for test": { en: "Force delivery failure for test", zh: "测试时强制投递失败" },
  "Same Feishu chat should keep reusing the same internal conversation once a mapping exists.": {
    en: "Same Feishu chat should keep reusing the same internal conversation once a mapping exists.",
    zh: "映射建立后，同一个飞书聊天会持续复用同一个内部会话。"
  },
  "Request Payload": { en: "Request Payload", zh: "请求载荷" },
  "Agent Response": { en: "Agent Response", zh: "Agent 回复" },
  "Delivery Result": { en: "Delivery Result", zh: "投递结果" },
  "Failed deliveries stay visible for retry and debugging.": {
    en: "Failed deliveries stay visible for retry and debugging.",
    zh: "失败投递会保留显示，方便重试和调试。"
  },
  "Check completion, streaming, and tool-calling support before switching the agent to a new model.": {
    en: "Check completion, streaming, and tool-calling support before switching the agent to a new model.",
    zh: "切换 Agent 使用新模型前，先检查补全、流式输出和工具调用支持。"
  },
  "Completion Preview": { en: "Completion Preview", zh: "补全预览" },
  "Stream Preview": { en: "Stream Preview", zh: "流式预览" },
  "Tool Calls": { en: "Tool Calls", zh: "工具调用" },
  "Build a provider first, then run validation. For local-only testing, `mock://success/openai` and `mock://success/ollama` also work as deterministic dry-run endpoints.": {
    en: "Build a provider first, then run validation. For local-only testing, `mock://success/openai` and `mock://success/ollama` also work as deterministic dry-run endpoints.",
    zh: "先创建供应商，再运行验证。本地纯测试时，也可以使用 `mock://success/openai` 和 `mock://success/ollama` 作为确定性的 dry-run 端点。"
  },
  "Keep the selected local adapter warm in memory so reply latency stays stable between turns.": {
    en: "Keep the selected local adapter warm in memory so reply latency stays stable between turns.",
    zh: "让所选本地适配器常驻内存，使多轮回复延迟保持稳定。"
  },
  "Warm Selected": { en: "Warm Selected", zh: "预热所选" },
  "Evict Selected": { en: "Evict Selected", zh: "释放所选" },
  "This local adapter has not reported runtime state yet.": {
    en: "This local adapter has not reported runtime state yet.",
    zh: "这个本地适配器尚未上报运行状态。"
  },
  "Runtime Config": { en: "Runtime Config", zh: "运行配置" }
};
