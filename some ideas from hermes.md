# Some Ideas From Hermes

This note collects ideas from Nous Research's Hermes Agent that may be useful for future Laiver optimization.

The goal is not to copy Hermes. Hermes is primarily an operating agent that learns how to work with a user across sessions. Laiver is a long-term personalized companion, so the useful parts are the memory mechanics, lifecycle hooks, and procedural-learning patterns, not the full product shape.

## References

- Hermes persistent memory: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/
- Hermes memory providers: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers/
- Hermes skills system: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/
- Hermes architecture: https://hermes-agent.nousresearch.com/docs/developer-guide/architecture/
- Hermes memory provider plugin guide: https://hermes-agent.nousresearch.com/docs/developer-guide/memory-provider-plugin/
- Laiver Memory V2 ADR: `docs/adrs/0006-companion-memory-v2.md`
- Laiver memory implementation plan: `docs/plans/2026-04-23-laiver-memory-system-implementation-plan.md`

## Executive Summary

Hermes is valuable because it treats memory as several different things:

- stable prompt-level memory
- searchable conversation history
- external memory-provider integration
- skills as procedural memory
- session lifecycle hooks for learning and synchronization

Laiver already has a stronger companion-oriented memory core than Hermes: `memory_episode`, `memory_fact`, `memory_revision`, `user_profile`, `relationship_state`, `memory_candidate`, gated writes, decay, and memory governance. The most useful Hermes-inspired direction is therefore to add a few operational layers around Laiver Memory V2:

1. a tiny always-on prompt memory snapshot
2. a separate conversation search layer
3. provider-style memory lifecycle hooks
4. reflection and repair jobs
5. procedural memory through skill candidates
6. stronger memory governance and traceability

## Objective Fit

Hermes seems optimized for:

- a coding or operating agent that gets better at executing tasks
- remembering user preferences and workflow conventions
- carrying useful project knowledge between sessions
- loading skills only when needed
- adding third-party memory systems without replacing the built-in baseline

Laiver is optimized for:

- long-term personalized companionship
- relationship continuity
- persona and emotional context
- user-visible memory governance
- changing preferences and temporal memory
- companion-style recall rather than pure task execution

This means Hermes should be treated as an engineering inspiration, not as a target architecture.

## Idea 1: Prompt Memory Snapshot

### Hermes Inspiration

Hermes keeps small persistent files such as `MEMORY.md` and `USER.md`. These are compact, stable, and injected into the system context at the start of a session.

### Why It Matters For Laiver

Laiver's Memory V2 is strong, but retrieval-based memory can be unstable. Some facts should not need retrieval every turn:

- user's preferred interaction style
- relationship tone
- important boundaries
- current long-term goals
- stable persona alignment
- important "do not forget" rules

For a companion, this always-on layer is important because it makes the agent feel continuous before retrieval even happens.

### Proposed Laiver Shape

Add a `prompt_memory_snapshot` concept generated from:

- `user_profile`
- `relationship_state`
- selected high-confidence `memory_fact`
- explicit user rules
- active persona card

Possible structure:

```text
PromptMemorySnapshot
- user_identity_summary
- durable_preferences
- communication_style
- relationship_state_summary
- active_long_term_goals
- boundaries_and_safety_notes
- explicit_user_rules
- last_refreshed_at
- source_fact_ids
```

### Design Constraints

- Keep it tiny. Suggested target: 800-1500 tokens.
- Only include stable, high-confidence, user-approved, or repeatedly reinforced information.
- Do not put arbitrary episodic memories here.
- Rebuild it deterministically from canonical memory state.
- Show it in the debug UI.
- Allow the user to inspect and correct it.

### Priority

P0. This is probably the highest-leverage Hermes-inspired improvement for Laiver.

## Idea 2: Separate Conversation Search From Fact Memory

### Hermes Inspiration

Hermes uses searchable session history for past conversations, separate from its compact persistent prompt memory.

### Why It Matters For Laiver

Laiver currently has episodes, facts, and general memory retrieval. But the product should make a clear conceptual distinction:

- "What should I currently believe about the user?"
- "What exactly did we talk about before?"

Those are different retrieval problems.

### Proposed Laiver Shape

Add or formalize a `conversation_search` read path:

- full-text search over raw messages and imported conversations
- optional vector search over conversation chunks
- result snippets with source links
- temporal filters
- persona/user filters
- exact phrase support

Use it for queries like:

- "What did we say last time?"
- "Find the paragraph where I mentioned..."
- "What was the name of that project?"
- "Show me the original message."

Keep `memory_fact` for current structured truths:

- preferences
- instructions
- habits
- boundaries
- relationship clues
- active goals

### Priority

P0/P1. It will reduce pressure on fact memory and make recall more trustworthy.

## Idea 3: Provider-Style Memory Interface

### Hermes Inspiration

Hermes memory providers are additive. Built-in memory remains active, while external providers can add prefetching, turn sync, extraction, or search.

### Why It Matters For Laiver

Laiver should not depend on a third-party memory provider for its core companion identity. But a provider interface would help modularize the current memory service and make experiments safer.

### Proposed Laiver Shape

Create a local-first memory provider interface. The default provider should be Laiver Memory V2.

Possible hooks:

```text
MemoryProvider
- prefetch_for_turn(user_id, persona_id, message, context)
- search(query, route, filters)
- write_candidate(event)
- commit_fact(candidate_id)
- sync_turn(user_message, assistant_message, debug_context)
- on_session_end(session_id)
- on_pre_compress(messages)
- run_maintenance(scope)
- explain(memory_ids)
```

External providers such as Hindsight, Honcho, Mem0, or Supermemory could later be implemented as optional secondary providers.

### Design Constraints

- External providers must be additive, not authoritative.
- The canonical source of companion memory should remain Laiver's database.
- Every external memory result needs provenance.
- Sensitive memory should not be sent to external providers by default.
- Provider output should enter review or traceable candidate state before becoming canonical.

### Priority

P1. Useful after the current `memory_service.py` becomes too concentrated.

## Idea 4: Reflection And Repair Loop

### Hermes Inspiration

Hermes and related memory-provider systems emphasize session-end extraction and reflection. Hindsight-like systems also focus on retaining, recalling, and reflecting over prior context.

### Why It Matters For Laiver

Companion memory should not only write facts during a turn. It should periodically repair itself:

- catch contradictions
- merge duplicates
- decay weak facts
- update relationship state
- find important missed moments
- produce memory candidates for review

This is closer to "growth" than immediate memory writes.

### Proposed Laiver Shape

Add a `reflect_maintenance` job separate from basic decay maintenance.

Possible phases:

1. collect recent conversations and memory writes
2. detect important uncommitted facts
3. detect contradictions and stale assumptions
4. propose merges or supersedes
5. update relationship state
6. refresh prompt memory snapshot
7. create review candidates
8. emit a memory trace report

### Priority

P1. This is central to a growing companion, but it should build on reliable memory governance.

## Idea 5: Procedural Memory Through Skill Candidates

### Hermes Inspiration

Hermes treats skills as a form of procedural memory. A skill is not just a tool; it is a remembered way of doing work.

### Why It Matters For Laiver

If Laiver is meant to grow with the user, it should learn not only facts about the user but also shared procedures:

- how the user likes to make decisions
- how the user wants code reviewed
- how the user likes brainstorming sessions
- how the user wants emotional conversations handled
- how the user wants project plans converted into implementation steps

This is different from declarative memory.

### Proposed Laiver Shape

Add `skill_candidate` or `procedure_candidate`.

Example candidate:

```text
Name: Product design grilling workflow
Trigger: user asks to stress-test a product idea
Procedure:
1. clarify the target user
2. identify the core promise
3. challenge the riskiest assumption
4. ask one question at a time
5. summarize decisions into implementation notes
Sources: conversation ids
Status: pending_review
```

After user approval, this can become:

- an active skill
- a prompt-level behavior rule
- a workflow template
- a project-specific Codex instruction

### Priority

P1. This may be the biggest "growing with me" feature after prompt memory.

## Idea 6: Memory Governance As Product Surface

### Hermes Inspiration

Hermes has simple, user-visible persistent memory files. That simplicity makes memory inspectable.

### Why It Matters For Laiver

Laiver already has a memory debug page and review queue. To feel trustworthy as a companion, memory cannot be a black box.

### Proposed Laiver Shape

Improve the memory UI around user questions:

- What do you currently believe about me?
- Why do you believe this?
- When did you learn it?
- When did you last use it?
- Is it still true?
- Can this be used in normal chat?
- Is this private, sensitive, or external-provider-blocked?
- What replaced this older belief?

Actions:

- approve
- reject
- edit
- merge
- supersede
- forget
- mark sensitive
- pin into prompt snapshot
- remove from prompt snapshot

### Priority

P0/P1. Companion memory needs governance as a first-class product feature.

## Idea 7: Explicit Memory Budgets

### Hermes Inspiration

Hermes constrains persistent prompt memory by size. This forces memory to stay sharp.

### Why It Matters For Laiver

Without budgets, memory systems accumulate vague summaries and low-value facts. For a companion, bloated memory can make the agent feel less precise, not more alive.

### Proposed Laiver Shape

Define budgets by memory layer:

```text
Prompt snapshot: 800-1500 tokens
Turn retrieval: 5-12 memory items
Relationship summary: 200-400 tokens
User profile summary: 300-700 tokens
Conversation search snippets: 3-8 snippets
Skill/procedure hints: 1-3 active procedures
```

Ranking should consider:

- recency
- importance
- confidence
- reinforcement count
- user approval
- sensitivity
- current route
- relationship relevance
- exact phrase match

### Priority

P1.

## Idea 8: Memory Trace For Every Response

### Hermes Inspiration

Hermes's architecture makes memory sources relatively explicit: prompt memory, session search, provider memory, skills.

### Why It Matters For Laiver

Laiver should be able to explain which memory sources affected a response. This is especially important when responses feel personal or emotionally loaded.

### Proposed Laiver Shape

Every agent response should be able to expose a trace like:

```text
MemoryTrace
- prompt_snapshot_version
- retrieved_facts
- retrieved_episodes
- conversation_search_hits
- relationship_state_version
- skills_or_procedures_used
- candidates_written
- facts_reinforced
- facts_superseded
- sensitive_memories_excluded
```

This should be visible in debug mode first, then possibly in user-facing "why did you say that?" flows.

### Priority

P0/P1. It pairs well with the existing memory debug direction.

## Idea 9: Additive External Memory Experiments

### Hermes Inspiration

Hermes supports external providers such as Honcho, Mem0, Hindsight, Holographic, ByteRover, and Supermemory.

### Why It Matters For Laiver

External providers can be useful for benchmarking and comparison, but they should not own the companion's core memory.

### Proposed Laiver Shape

Run external providers only as optional experiments:

- mirror non-sensitive session summaries
- compare recall quality
- compare relationship continuity
- compare entity resolution
- compare long-horizon retrieval
- compare conflict handling

Potential experiment modes:

```text
off: no external memory
shadow: send allowed data and log provider suggestions, but do not use them
assistive: use provider suggestions in debug only
active: allow provider recall into prompt with trace and safety gates
```

### Priority

P2. Useful, but only after local memory governance is reliable.

## Idea 10: User Memory And Agent Memory Should Be Separate

### Hermes Inspiration

Hermes separates user memory from agent/project memory.

### Why It Matters For Laiver

Laiver should separate:

- memory about the user
- memory about the persona
- memory about the relationship
- memory about projects
- memory about tools and environment
- memory about learned procedures

Mixing these together makes retrieval and governance harder.

### Proposed Laiver Shape

Introduce clearer memory domains:

```text
user_profile_memory
relationship_memory
persona_self_memory
project_memory
environment_memory
procedural_memory
conversation_archive
```

This does not necessarily require separate tables immediately. It can start as a domain field and retrieval route.

### Priority

P1.

## Idea 11: Session Start And Session End Rituals

### Hermes Inspiration

Hermes has session-level memory behavior: load stable memory at start, update or sync at end.

### Why It Matters For Laiver

A growing companion needs lifecycle moments. Not every update should happen inside the real-time chat path.

### Proposed Laiver Shape

At session start:

- load prompt memory snapshot
- load active persona
- load relationship state
- retrieve recent active arcs
- prefetch likely relevant memories

At session end:

- summarize unresolved arcs
- write candidate memories
- update relationship state
- update active goals
- refresh prompt memory snapshot if needed
- schedule reflection job

### Priority

P1.

## Idea 12: Active Arcs

### Hermes Inspiration

Hermes's persistent memory and session history help carry work across sessions. Laiver can adapt this for emotional and life continuity.

### Why It Matters For Laiver

Companionship is not just facts. It includes ongoing arcs:

- the user is building Laiver
- the user is exploring companion memory
- the user is worried about X
- the user is preparing for Y
- the user is changing their mind about Z

### Proposed Laiver Shape

Add `active_arc` as either a memory fact subtype or relationship/profile field.

Fields:

```text
ActiveArc
- title
- type: project | emotional | relationship | learning | decision | habit
- status
- summary
- last_touched_at
- next_expected_checkin
- source_episode_ids
- sensitivity
```

Use active arcs in prompt memory and retrieval ranking.

### Priority

P1. Very aligned with "grow with me."

## Idea 13: Memory Confidence Should Be Lived, Not Static

### Hermes Inspiration

Hermes's compact memory model forces a distinction between durable facts and less stable history.

### Why It Matters For Laiver

For a companion, confidence should change as the relationship evolves:

- reinforced memories become stronger
- stale preferences decay
- contradicted facts become candidates for supersede
- sensitive facts may require confirmation before use

### Proposed Laiver Shape

Expand scoring around:

- confidence
- importance
- emotional weight
- stability
- sensitivity
- last confirmed at
- last contradicted at
- last used at
- user approval status

Then use these scores differently by route:

- fast chat route: only stable, safe, high-confidence facts
- reflective route: broader context and uncertain candidates
- relationship route: relationship and emotional continuity
- project route: project and procedural memory

### Priority

P1.

## Idea 14: Human-Readable Memory Files As Export

### Hermes Inspiration

Hermes's `MEMORY.md` and `USER.md` are simple and inspectable.

### Why It Matters For Laiver

Even if Laiver stores canonical memory in tables, a human-readable export can make the system feel controllable.

### Proposed Laiver Shape

Add export views:

```text
laiver-user-memory.md
laiver-relationship-memory.md
laiver-project-memory.md
laiver-procedural-memory.md
```

These should be generated from canonical state, not edited as the source of truth initially.

Later, allow user-edited imports through a review flow.

### Priority

P2.

## Idea 15: Memory As A Contract With The User

### Hermes Inspiration

Hermes's small persistent files imply a contract: this is what the agent knows and will carry forward.

### Why It Matters For Laiver

For a companion, memory is intimate. The user should be able to define how memory behaves.

### Proposed Laiver Shape

Add user-level memory policy:

```text
MemoryPolicy
- allow_memory_writes
- require_review_for_personal_facts
- require_review_for_sensitive_facts
- allow_relationship_state_updates
- allow_prompt_snapshot_pinning
- allow_external_provider_shadowing
- allow_external_provider_active_recall
- default_retention
- forgetfulness_preference
```

This should eventually be surfaced in Settings.

### Priority

P1/P2 depending on how quickly Laiver handles sensitive memories.

## Idea 16: Context Router Before Retrieval

### Hermes Inspiration

Hermes uses different memory and skill mechanisms depending on the situation.

### Why It Matters For Laiver

Laiver should not retrieve all memory types for every message. The agent should first decide what kind of turn this is.

### Proposed Laiver Shape

Before retrieval, classify the turn:

```text
TurnRoute
- fast_reply
- emotional_support
- relationship_continuity
- project_work
- memory_lookup
- exact_conversation_search
- planning
- skill_execution
- reflection
```

Then choose memory sources:

```text
fast_reply:
  prompt_snapshot only, maybe 1-3 facts

memory_lookup:
  conversation search + facts + episodes

relationship_continuity:
  prompt_snapshot + relationship_state + active_arcs

project_work:
  project memory + procedural memory + recent context

reflection:
  broad facts + episodes + candidates + contradictions
```

### Priority

P1.

## Idea 17: Companion Self-Memory

### Hermes Inspiration

Hermes has agent/project memory distinct from user memory.

### Why It Matters For Laiver

If Laiver has personas, the persona needs continuity too. This should not be confused with the user's profile.

### Proposed Laiver Shape

Add `persona_self_memory`:

- persona's stable style
- boundaries
- known promises
- relationship stance
- growth notes
- things the persona should avoid pretending

This should be generated from persona config plus approved relationship memories.

### Priority

P2, but important for high-quality companion behavior.

## Idea 18: Memory Evals Inspired By Hermes Layers

### Hermes Inspiration

Hermes splits memory into different retrieval and persistence mechanisms.

### Why It Matters For Laiver

Laiver already has memory regression cases. Future evals should test the layers separately.

### Proposed Eval Families

```text
prompt_snapshot_eval:
  stable user preference appears without retrieval

conversation_search_eval:
  exact old phrase can be found without becoming a fact

fact_revision_eval:
  changed preference supersedes old preference

relationship_continuity_eval:
  tone and relationship state evolve over many sessions

procedural_memory_eval:
  approved workflow is recalled and used

external_provider_shadow_eval:
  provider suggestion is logged but not canonical

sensitive_memory_eval:
  sensitive memory is gated and excluded from normal recall
```

### Priority

P0/P1. Every major memory change should have an eval.

## Suggested Roadmap

### Phase 1: Stabilize Always-On Memory

- Add `prompt_memory_snapshot`.
- Add debug UI display for snapshot contents.
- Add source fact links.
- Add eval for stable preference and relationship style.

### Phase 2: Split Recall Paths

- Add or formalize `conversation_search`.
- Route exact/history questions to conversation search.
- Keep facts for current beliefs.
- Add eval for exact phrase and "last time" recall.

### Phase 3: Add Reflection

- Add session-end memory candidate generation.
- Add reflection maintenance for merge/supersede/missed facts.
- Update relationship state through reflection, not only immediate writes.
- Add trace reports.

### Phase 4: Procedural Memory

- Add procedure/skill candidates.
- Let user approve learned workflows.
- Inject active procedures into prompt only when relevant.
- Add eval for workflow recall.

### Phase 5: Provider Experiments

- Define `MemoryProvider`.
- Wrap Laiver Memory V2 as the default provider.
- Add external providers only in shadow mode first.
- Compare recall quality and privacy risk before active use.

## Non-Goals

- Do not replace Laiver Memory V2 with Hermes's memory model.
- Do not make external memory providers canonical.
- Do not put all history into prompt memory.
- Do not convert every conversation detail into a fact.
- Do not add graph storage until real query patterns justify it.
- Do not hide memory behavior from the user.

## Key Architectural Principle

For Laiver, memory should be layered like this:

```text
Current turn context
  -> Prompt memory snapshot
  -> Relationship state
  -> Active arcs
  -> Structured facts
  -> Conversation search
  -> Episodes and provenance
  -> Procedural skills
  -> Optional external providers
```

Hermes shows that a useful agent needs more than vector recall. The lesson for Laiver is to make memory operational, inspectable, layered, and lifecycle-aware, while preserving Laiver's stronger companion-specific model of facts, revisions, relationship state, and user governance.

