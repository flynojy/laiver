# Laiver Memory Eval Matrix

最后更新日期：2026-05-08

本文档记录当前 Memory 回归评估基线。目标不是替代完整集成测试，而是在继续修改 retrieval、governance、profile、relationship 或 long-horizon memory 行为前，提供一组可重复、可解释、能快速定位退化的 memory eval cases。

运行入口：

```powershell
python scripts/evals/run_memory_regression.py
```

可选只跑单个 case：

```powershell
python scripts/evals/run_memory_regression.py --case profile_preference_recall
```

输出 JSON：

```powershell
python scripts/evals/run_memory_regression.py --json
```

## 当前 Cases

| Case | 覆盖目标 | 关键断言 |
| --- | --- | --- |
| `profile_preference_recall` | 用户偏好类事实应优先被 profile / preference 路线召回 | 搜索结果非空；Top result 是 `preference`；内容包含 `concise answers` |
| `episodic_recall` | “last time / 上次”类问题应优先召回 episodic memory | 搜索结果非空；Top result 是 `episodic`；内容包含 `launch checklist` |
| `exact_phrase_recall` | 姓名、短语、原话片段应通过 exact / full-text 候选集被优先召回 | 搜索结果非空；Top result 是 `episodic`；内容包含 `Alice` 和 `release summary` |
| `chat_grounding` | 第二轮对话应能利用第一轮写入的长期记忆 grounding 回复 | 第一轮写入 memory；第二轮使用 `memory-search`；回复和 memory hits 包含用户偏好 |
| `duplicate_reinforcement` | 重复偏好写入应 reinforcement，而不是创建重复 fact | 两次写入返回同一 memory；reinforcement / duplicate count 为 2；profile 和 relationship snapshot 更新 |
| `conflict_supersede` | 冲突 instruction 应 supersede 旧版本，并更新 profile | 旧 memory archived；新 memory active；profile 包含新 instruction 且不包含旧 instruction |
| `gated_candidate_approval` | 低置信或 requires-review 的候选记忆应先进入 review queue，批准后再写入 canonical fact | 初始 memory 是 `pending_review`；candidate 无 fact；approve 后生成 fact；memory 变为 active |

## 设计约定

- 每个 case 使用独立 SQLite 临时数据库，避免跨 case 污染。
- 所有 case 走 API 层，不直接调用 service 内部函数。
- Mock provider、mock fine-tune、local adapter mock runtime 是可重复评估的一部分，不应在没有替代方案前移除。
- 当前 eval 关注 regression guard，不声称衡量真实陪伴质量。

## 后续扩展

下一批可补：

- exact / full-text memory search：继续扩展中文姓名、专有名词和更长原话片段。
- relationship continuity：多轮对话后 relationship state 的 warmth / familiarity / preferred tone 是否稳定更新。
- maintenance effects：decay、archive、stale candidate ignore 之后是否影响 active recall。
- privacy / sensitivity：敏感 memory 是否进入 gated flow，以及是否默认排除在普通 recall 外。
- LongMemEval / LoCoMo-inspired fixture：引入更长对话、时间跨度和多实体关系。
