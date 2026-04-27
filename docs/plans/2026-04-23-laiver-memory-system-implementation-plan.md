# Laiver Memory System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade laiver from a single-record memory system into a long-horizon companion memory stack built around episode ingestion, temporal fact revisions, structured profile state, relationship continuity, and explainable retrieval.

**Architecture:** Keep the current FastAPI + PostgreSQL + Qdrant backbone, and evolve it incrementally. Add `memory_episode`, `memory_fact`, `memory_revision`, `user_profile`, `relationship_state`, and `memory_candidate` as first-class domains. Keep the current `Memory` table working during migration, but make the new system the source of truth for long-term companion memory. Use multi-route retrieval instead of one global similarity search, and keep graph capabilities out of MVP unless relation queries become the primary bottleneck.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, Qdrant, Next.js, background worker built on existing app runtime

---

## 1. Why This Plan Exists

laiver is a long-term personalized AI companion, not an enterprise knowledge base assistant. The memory system therefore has to optimize for:

1. relationship continuity across long time horizons
2. stable understanding of user preferences, rules, and emotional context
3. change over time, including superseded preferences and evolving relationship tone
4. user-visible governance, not opaque storage

The current repository already supports:

- instruction / preference / episodic / session classification
- duplicate reinforcement
- conflict supersede
- long-term summary generation
- reranked memory recall
- memory debug UI

That is a strong base. The next step is to convert memory from "ranked notes" into a durable companion memory model with provenance, revisions, profile state, relationship state, and explainable recall.

## 2. Target Architecture Summary

### 2.1 Memory Layers

The target system should have six layers:

1. `working_memory`
   - current turn and short sliding context
   - already mostly represented by recent conversation state

2. `session_memory`
   - recent temporary context, such as "this week I am preparing for interviews"

3. `memory_episode`
   - append-only source events from chats, imports, skills, and tools
   - the provenance ledger for later fact extraction

4. `memory_fact`
   - current structured facts about the user, the dyad, or related entities
   - includes preferences, instructions, habits, boundaries, identity clues, and relationship clues

5. `user_profile`
   - structured current snapshot rebuilt from active facts

6. `relationship_state`
   - current state of the user-agent relationship
   - warmth, trust, familiarity, active arcs, sensitivities, and interaction style

### 2.2 Design Principles

- preserve history instead of overwriting it
- use revisions for change over time
- separate raw episodes from distilled facts
- make relationship state first-class
- do not introduce a graph database in MVP
- keep user-facing governance and explainability in scope from the start

## 3. MVP / V2 / V3 Scope

### MVP

Required for the first meaningful upgrade:

- episode ledger
- fact + revision model
- user profile snapshot
- relationship state snapshot
- review queue for uncertain memory writes
- multi-route retrieval
- memory trace / explainability
- typed decay policy
- conversation search vs fact search split

### Progress Update (2026-04-23)

Completed in the current repository:

- episode ledger is implemented and visible in the memory debug UI
- fact + revision model is implemented, including reinforce and supersede flows
- user profile snapshot and relationship state snapshot are persisted and visible
- multi-route retrieval is implemented for profile / instruction / episodic paths
- review queue MVP is now implemented for `memory_candidate`
  - `write_memory()` emits review candidates for user-origin instruction / preference / episodic writes
  - debug state exposes candidate counts and recent candidates
  - API supports listing and reviewing candidates
  - memory UI supports approve / reject actions for pending candidates
- uncertain-write gating is implemented for low-confidence, sensitive, or explicitly review-required instruction / preference writes
  - gated writes create an episode, a memory row, and a pending candidate
  - gated writes do not create `memory_fact` / `memory_revision` until approval
  - approval promotes the memory into canonical fact / revision state and refreshes profile snapshots
  - rejection keeps the candidate auditable and marks the gated memory as ignored
- memory consolidation / decay maintenance is implemented as a runnable backend task
  - active facts decay according to `decay_policy`
  - weak decayed facts are archived and removed from active recall
  - stale pending candidates are marked ignored
  - affected user profile and relationship snapshots are rebuilt
  - the task can run periodically from FastAPI lifespan or manually through `/memories/maintenance/run`

Still pending inside the broader plan:

- benchmark harness for long-memory evaluation
- deeper governance flows such as rollback, merge, and privacy tiers

### V2

- entity extraction and relation tables
- scheduled consolidation jobs
- profile patch engine
- sensitive memory policy
- benchmark harness for long-memory eval
- optional relation expansion in retrieval

### V3

- temporal graph or graph traversal read-path
- retrospective repair loop
- proactive resurfacing of meaningful memories
- memory privacy tiers
- cross-skill or cross-agent shared memory governance

## 4. Proposed Core Schema

### 4.1 `memory_episode`

Append-only record of raw source events.

Key fields:

- `id`
- `user_id`
- `persona_id`
- `conversation_id`
- `source_type`
- `source_ref`
- `speaker_role`
- `occurred_at`
- `raw_text`
- `structured_payload`
- `summary_short`
- `summary_medium`
- `importance`
- `emotional_weight`
- `embedding_vector_id`
- `created_at`

### 4.2 `memory_fact`

Logical current memory unit.

Key fields:

- `id`
- `user_id`
- `persona_id`
- `fact_type`
- `subject_kind`
- `subject_ref`
- `predicate_key`
- `value_text`
- `value_json`
- `normalized_key`
- `status`
- `current_revision_id`
- `confidence`
- `importance`
- `stability_score`
- `reinforcement_count`
- `source_count`
- `effective_from`
- `effective_to`
- `last_confirmed_at`
- `last_used_at`
- `decay_policy`
- `sensitivity`
- `created_at`
- `updated_at`

### 4.3 `memory_revision`

Event history for a fact.

Key fields:

- `id`
- `fact_id`
- `revision_no`
- `op`
- `content_text`
- `value_json`
- `confidence_delta`
- `source_episode_id`
- `supersedes_revision_id`
- `conflict_group_id`
- `valid_from`
- `valid_to`
- `author_type`
- `reason_codes`
- `created_at`

### 4.4 `user_profile`

Structured current snapshot of long-lived user understanding.

Key fields:

- `user_id`
- `core_identity_json`
- `communication_style_json`
- `stable_preferences_json`
- `boundaries_json`
- `life_context_json`
- `profile_summary`
- `profile_version`
- `source_fact_count`
- `last_rebuilt_at`
- `confidence`

### 4.5 `relationship_state`

Structured dyad state between the user and a persona.

Key fields:

- `id`
- `user_id`
- `persona_id`
- `relationship_stage`
- `warmth_score`
- `trust_score`
- `familiarity_score`
- `preferred_tone`
- `active_topics_json`
- `recurring_rituals_json`
- `recent_sensitivities_json`
- `unresolved_tensions_json`
- `last_meaningful_interaction_at`
- `last_repair_at`
- `summary`
- `version`
- `updated_at`

### 4.6 `memory_candidate`

Candidate fact extraction queue before commit.

Key fields:

- `id`
- `user_id`
- `persona_id`
- `episode_id`
- `candidate_type`
- `extracted_text`
- `normalized_key`
- `proposed_value_json`
- `proposed_action`
- `salience_score`
- `confidence_score`
- `sensitivity`
- `reason_codes_json`
- `auto_commit`
- `status`
- `reviewer_type`
- `created_at`
- `processed_at`

## 5. Retrieval Architecture

### 5.1 Retrieval Routes

Introduce a memory router that classifies the query into one or more routes:

- `profile`
- `relationship`
- `instruction`
- `episodic`
- `entity`
- `conversation_search`
- `tool_or_skill_context`

### 5.2 Retrieval Fusion

Each request may combine:

- structured fact lookup
- vector episodic recall from Qdrant
- PostgreSQL full-text / keyword search
- optional relation expansion in V2

Rank with:

- reciprocal rank fusion for candidate merge
- a local rerank stage using score features and, later, a reranker model

### 5.3 Scoring Inputs

- semantic relevance
- keyword match
- current revision priority
- reinforcement count
- confidence
- importance
- access history
- temporal weight
- source reliability
- sensitivity policy

## 6. Write Pipeline

### 6.1 Hot Path

Run inline for:

- explicit "remember this"
- explicit preference
- explicit instruction or boundary
- user corrections
- high-confidence conflict updates

### 6.2 Background Path

Run asynchronously for:

- candidate extraction from dialogue windows
- salience scoring
- uncertainty handling
- profile rebuild
- relationship refresh
- long-form consolidation

### 6.3 Canonical Pipeline

`turn -> episode append -> candidate extraction -> salience scoring -> dedupe / conflict resolution -> fact revision write -> profile refresh -> relationship refresh -> retrieval index refresh`

## 7. Decay and Supersede Policy

### 7.1 Fact Policies

- `identity` and explicit boundaries: near-zero decay
- stable preferences: slow decay
- situational preferences: medium decay
- episodic details: fast decay
- transient emotional state: very fast decay unless reinforced

### 7.2 Supersede Rules

- never delete old conflicting facts
- close old validity window
- create new revision or new fact depending on resolution type
- keep old state available for audit and timeline views
- exclude superseded revisions from default recall

## 8. UI and Governance Requirements

The current memory page should evolve into these user-visible views:

- Profile
- Relationship
- Timeline
- Facts
- Conflict Groups
- Review Queue
- Memory Trace

Each memory view should show:

- source episode
- why it exists
- whether it is active
- whether it is superseded
- when it was last used
- what profile or relationship field it affects

Supported actions:

- pin
- archive
- supersede
- merge
- split
- correct
- mark sensitive
- set TTL
- reject candidate

## 9. Migration Strategy

The existing `Memory` table should stay alive during migration.

Recommended migration path:

1. keep `Memory` as compatibility storage and UI source for the current release
2. add new episode / fact / revision tables
3. dual-write new conversations into both systems
4. backfill high-value current memories into fact + revision
5. switch retrieval for selected routes to the new system
6. switch profile generation and explainability to the new system
7. deprecate the old write path only after parity is proven

## 10. Implementation Tasks

### Task 1: Create the architecture and migration ADR

**Files:**
- Create: `docs/adrs/0006-companion-memory-v2.md`
- Modify: `docs/architecture.md`
- Modify: `docs/plans/2026-04-23-laiver-memory-system-implementation-plan.md`

**Goal:** Record the decision to evolve from single-record memories to episode + fact + revision architecture without introducing a graph database in MVP.

**Implementation Notes:**
- document why `relationship_state` is first-class
- document why graph is deferred
- document source-of-truth rules

**Verification:**
- doc reviewed for consistency with repository structure

### Task 2: Add new database models and Alembic migrations

**Files:**
- Create: `apps/api/alembic/versions/20260423_0006_companion_memory_v2.py`
- Create: `apps/api/app/models/memory_episode.py`
- Create: `apps/api/app/models/memory_fact.py`
- Create: `apps/api/app/models/memory_revision.py`
- Create: `apps/api/app/models/user_profile.py`
- Create: `apps/api/app/models/relationship_state.py`
- Create: `apps/api/app/models/memory_candidate.py`
- Modify: `apps/api/app/models/__init__.py`
- Modify: `apps/api/app/db/base.py`
- Modify: `apps/api/app/models/user.py`
- Modify: `apps/api/app/models/conversation.py`

**Goal:** Land the storage primitives for the new memory model.

**Implementation Notes:**
- use UUID primary keys
- use JSON columns for structured summary fields
- add indexes on `user_id`, `persona_id`, `predicate_key`, `normalized_key`, `status`
- add validity window fields on facts / revisions

**Verification:**
- run Alembic migration upgrade
- instantiate models in tests

### Task 3: Add schemas and API contracts for the new memory domain

**Files:**
- Create: `apps/api/app/schemas/memory_episode.py`
- Create: `apps/api/app/schemas/memory_fact.py`
- Create: `apps/api/app/schemas/user_profile.py`
- Create: `apps/api/app/schemas/relationship_state.py`
- Create: `apps/api/app/schemas/memory_candidate.py`
- Modify: `apps/api/app/schemas/__init__.py`
- Modify: `packages/shared/src/types.ts`
- Modify: `apps/web/lib/api.ts`

**Goal:** Expose strongly typed contracts for backend and frontend work.

**Implementation Notes:**
- define read and update schemas separately
- keep MVP response shapes flat enough for the current dashboard
- keep trace payloads explicit

**Verification:**
- API type-checks cleanly
- web build compiles after shared type updates

### Task 4: Split the current memory service into focused modules

**Files:**
- Create: `apps/api/app/services/memory/__init__.py`
- Create: `apps/api/app/services/memory/episode_service.py`
- Create: `apps/api/app/services/memory/candidate_service.py`
- Create: `apps/api/app/services/memory/fact_service.py`
- Create: `apps/api/app/services/memory/revision_service.py`
- Create: `apps/api/app/services/memory/profile_service.py`
- Create: `apps/api/app/services/memory/relationship_service.py`
- Create: `apps/api/app/services/memory/retrieval_service.py`
- Create: `apps/api/app/services/memory/router_service.py`
- Create: `apps/api/app/services/memory/trace_service.py`
- Modify: `apps/api/app/services/memory_service.py`

**Goal:** Move from one large service file to a memory domain package with clear responsibilities.

**Implementation Notes:**
- keep `memory_service.py` as a facade during migration
- move shared scoring helpers into local utility functions
- preserve current API behavior while new services come online

**Verification:**
- existing memory integration tests still pass
- no behavior regression in current endpoints

### Task 5: Append source episodes on each write path

**Files:**
- Modify: `apps/api/app/services/agent_orchestrator.py`
- Modify: `apps/api/app/services/skill_runtime.py`
- Create: `apps/api/app/services/memory/episode_ingest.py`
- Test: `apps/api/tests/test_integration.py`

**Goal:** Every memory-worthy source event creates a `memory_episode`.

**Implementation Notes:**
- chat turns create episodes
- imports can batch-create episodes later
- skill/tool outputs should record source type and source reference

**Verification:**
- integration test confirms agent turns create episodes
- debug endpoint can show recent episodes

### Task 6: Build candidate extraction and review queue

**Files:**
- Modify: `apps/api/app/services/memory/candidate_service.py`
- Modify: `apps/api/app/services/agent_orchestrator.py`
- Create: `apps/api/app/api/routers/memory_candidates.py`
- Modify: `apps/api/app/api/router.py`
- Test: `apps/api/tests/test_integration.py`

**Goal:** Uncertain memories should be staged before they become active facts.

**Implementation Notes:**
- explicit instructions and explicit preferences can auto-commit
- emotional inference and sensitive inference should enter review
- candidate records should store reason codes and proposed action

**Verification:**
- integration tests for auto-commit and pending-review branches

### Task 7: Implement fact creation, reinforcement, and supersede with revisions

**Files:**
- Modify: `apps/api/app/services/memory/fact_service.py`
- Modify: `apps/api/app/services/memory/revision_service.py`
- Modify: `apps/api/app/services/memory_service.py`
- Test: `apps/api/tests/test_integration.py`

**Goal:** Replace current metadata-only supersede logic with durable fact revisions.

**Implementation Notes:**
- detect same-slot updates using `normalized_key`
- reinforcement increments counters and adds a revision
- supersede closes old validity window and creates a new current revision

**Verification:**
- tests for duplicate reinforcement
- tests for conflicting preference supersede
- tests for current revision recall filtering

### Task 8: Add structured profile and relationship refresh

**Files:**
- Modify: `apps/api/app/services/memory/profile_service.py`
- Modify: `apps/api/app/services/memory/relationship_service.py`
- Modify: `apps/api/app/services/agent_orchestrator.py`
- Test: `apps/api/tests/test_integration.py`

**Goal:** Replace plain summary-only memory profile with structured profile and relationship snapshots.

**Implementation Notes:**
- profile rebuild should aggregate active facts by type
- relationship state should aggregate tone, active arcs, sensitivities, and familiarity signals
- prompt assembly should consume compact core blocks

**Verification:**
- tests confirm profile and relationship snapshots update after writes
- debug payload includes current profile and relationship snapshots

### Task 9: Introduce retrieval routing and explainable memory trace

**Files:**
- Modify: `apps/api/app/services/memory/router_service.py`
- Modify: `apps/api/app/services/memory/retrieval_service.py`
- Modify: `apps/api/app/services/memory/trace_service.py`
- Modify: `apps/api/app/services/agent_orchestrator.py`
- Modify: `apps/api/app/schemas/agent.py`
- Test: `apps/api/tests/test_integration.py`

**Goal:** Retrieve different memory categories by intent and explain why a response used them.

**Implementation Notes:**
- route preference questions to profile and fact lookup first
- route "last time" questions to episodic recall first
- capture final trace with route, hits, rank reasons, and prompt blocks used

**Verification:**
- tests confirm query route changes selected memory set
- chat debug UI can render trace fields

### Task 10: Add full-text memory search alongside vector recall

**Files:**
- Modify: `apps/api/app/services/memory/retrieval_service.py`
- Modify: `apps/api/app/core/config.py`
- Create: `apps/api/app/services/memory/search_sql.py`
- Test: `apps/api/tests/test_integration.py`

**Goal:** Support exact and phrase recall for names, topics, and conversation snippets.

**Implementation Notes:**
- start with PostgreSQL FTS and trigram
- keep Qdrant for semantic episodic recall
- merge result sets with reciprocal rank fusion

**Verification:**
- exact phrase test
- semantic recall test
- mixed query test

### Task 11: Add memory governance API and dashboard surfaces

**Files:**
- Modify: `apps/api/app/api/routers/memories.py`
- Create: `apps/api/app/api/routers/memory_governance.py`
- Modify: `apps/web/app/(dashboard)/memories/page.tsx`
- Create: `apps/web/app/(dashboard)/memories/review-queue.tsx`
- Create: `apps/web/app/(dashboard)/memories/profile-panel.tsx`
- Create: `apps/web/app/(dashboard)/memories/relationship-panel.tsx`
- Create: `apps/web/app/(dashboard)/memories/trace-panel.tsx`
- Modify: `apps/web/lib/api.ts`

**Goal:** Make the upgraded memory system visible and editable in the dashboard.

**Implementation Notes:**
- add views for profile, relationship, facts, timeline, conflicts, review queue
- support approve / reject candidate actions
- support merge, supersede, archive, and sensitivity edits

**Verification:**
- web build passes
- manual dashboard smoke test

### Task 12: Add background consolidation jobs

**Files:**
- Create: `apps/api/app/services/memory/consolidation_service.py`
- Create: `apps/api/app/services/memory/job_runner.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/core/config.py`
- Test: `apps/api/tests/test_integration.py`

**Goal:** Support deferred candidate extraction, profile rebuild, and relationship refresh without blocking chat latency.

**Implementation Notes:**
- start with in-process scheduled or triggered jobs
- keep job payloads idempotent
- record job status for debugging

**Verification:**
- test that a queued consolidation job refreshes profile state

### Task 13: Add migration and backfill tooling

**Files:**
- Create: `scripts/memory/backfill_companion_memory.py`
- Create: `scripts/memory/verify_companion_memory_backfill.py`
- Modify: `README.md`

**Goal:** Backfill current high-value memory rows into the new fact-revision model.

**Implementation Notes:**
- only backfill active and pinned memories in the first pass
- map `instruction`, `preference`, `episodic` labels carefully
- generate a report instead of silent mutation

**Verification:**
- dry-run report
- sampled backfill validation

### Task 14: Add regression and benchmark harness

**Files:**
- Create: `scripts/evals/run_memory_regression.py`
- Create: `docs/plans/2026-04-23-memory-eval-matrix.md`
- Modify: `apps/api/tests/test_integration.py`

**Goal:** Track whether new memory behavior actually improves long-horizon companion recall.

**Implementation Notes:**
- include current reinforcement and supersede checks
- add profile, relationship, and episodic recall checks
- prepare hooks for LongMemEval / LoCoMo-inspired subsets later

**Verification:**
- local regression script passes
- CI can run targeted memory suite

## 11. Suggested Delivery Order

### P0

- Task 1
- Task 2
- Task 3
- Task 4
- Task 5
- Task 7
- Task 8
- Task 9

### P1

- Task 6
- Task 10
- Task 11
- Task 12
- Task 13

### P2

- Task 14
- relation tables
- optional graph proof-of-concept
- proactive memory features

## 12. Immediate Next Slice

The safest first implementation slice is:

1. add tables and schemas
2. dual-write episodes from chat turns
3. convert reinforcement / supersede to fact revisions
4. rebuild profile snapshot from facts
5. expose debug payload and basic UI

This slice preserves current behavior while establishing the new data model.

## 13. Verification Checklist

Backend:

- `python -m unittest discover -s apps/api/tests -p "test_*.py" -v`
- targeted tests for reinforcement, supersede, profile rebuild, relationship refresh, retrieval routing

Frontend:

- `npm.cmd run build:web`

Regression:

- `python scripts/run_mvp_regression.py`
- later: `python scripts/evals/run_memory_regression.py`

Manual checks:

- explicit preference write
- conflict update write
- "what do I prefer" query
- "what happened last time" query
- candidate review flow
- trace visibility in dashboard

## 14. Risks and Guardrails

Main risks:

- over-engineering too early
- profile drift from weak extraction
- relationship state becoming a vague summary blob
- migration confusion between old and new memory stores
- UI complexity outrunning backend stability

Guardrails:

- keep graph out of MVP
- keep old memory path during migration
- make every structured state traceable to facts and episodes
- gate low-confidence inference behind review queue
- validate each new retrieval route with explicit tests

## 15. Definition of Done for Memory V2 MVP

Memory V2 MVP is done when:

- new conversations create episodes
- explicit preference and instruction writes create facts with revisions
- conflicts create superseded history instead of metadata-only replacement
- profile and relationship state are rebuilt from active facts
- retrieval routes can distinguish preference, relationship, and episodic questions
- dashboard shows profile, conflicts, and traceability
- old memory flow still works during migration
- regression tests pass
