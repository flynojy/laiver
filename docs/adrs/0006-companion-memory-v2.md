# ADR-0006: Companion Memory V2 Architecture

- Status: Accepted
- Date: 2026-04-23

## Context

laiver is a long-term personalized AI companion. The existing memory system already supports classification, reinforcement, conflict supersede, profile summary, and reranked recall, but it still stores memory primarily as single records with metadata overlays.

That model is no longer enough for the next stage because laiver now needs:

- source provenance for each memory-worthy event
- structured facts that can change over time
- revision history instead of metadata-only replacement
- a first-class relationship state between user and persona
- explainable retrieval and user-visible governance

At the same time, the project should evolve incrementally on top of the current FastAPI, PostgreSQL, and Qdrant stack, without introducing unnecessary infrastructure risk.

## Decision

Adopt a companion-memory-v2 architecture built on:

1. `memory_episode`
   - append-only source events from chat, imports, skills, and tools

2. `memory_fact`
   - structured current facts derived from episodes

3. `memory_revision`
   - revision history for reinforcement, supersede, and user correction

4. `user_profile`
   - structured user snapshot rebuilt from active facts

5. `relationship_state`
   - dyadic state between user and persona

6. `memory_candidate`
   - staging area for uncertain or review-worthy memory extraction

The current `memories` table remains active during migration. New work should dual-write into the new structures where practical, then gradually move retrieval and profile generation to the v2 source of truth.

Graph storage is explicitly deferred from MVP. The MVP should use PostgreSQL tables plus Qdrant and only add relation tables or graph traversal later if real query patterns justify the extra complexity.

## Consequences

### Positive

- preserves history instead of overwriting it
- supports temporal change and active vs superseded memory cleanly
- makes profile and relationship state traceable to facts and episodes
- keeps the migration path incremental
- fits the current repository architecture and deployment shape

### Negative

- temporary dual-write complexity during migration
- more tables and services to coordinate
- retrieval logic becomes more explicit and therefore more code-heavy
- governance UI will need to expand beyond the current table view

## Follow-Up

- add the new Alembic migration and SQLAlchemy models
- introduce episode write paths before replacing current memory behavior
- move reinforcement and supersede to fact revisions
- add structured profile and relationship rebuild services
- add multi-route retrieval and memory trace support
