# ADR-0001: MVP Foundation Architecture

- Status: Accepted
- Date: 2026-03-17

## Context

平台一期目标需要在尽量短的迭代周期内，打通“导入 -> Persona -> Memory -> Chat -> Skill -> Connector”闭环，同时还要保持工程可扩展。

## Decision

采用模块化单体架构：

- 前端：Next.js App Router + TypeScript + Tailwind
- 后端：FastAPI + SQLAlchemy + Alembic
- 数据：PostgreSQL + Redis + Qdrant
- 代码组织：Monorepo + Shared Types

## Consequences

### Positive

- 开发速度快，适合 MVP
- 目录职责清晰，便于后续拆分
- 数据模型集中，迁移与调试成本更低

### Negative

- 业务复杂度上升后，单体服务可能成为扩展边界
- Web 与 API 需要分别管理依赖链

## Follow-Up

- 当 Connector 与 Skill Runtime 复杂度显著增加时，评估是否拆分为独立 worker / service
- 当多租户与权限需求明确后，引入 auth / RBAC 子系统

