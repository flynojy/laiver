# Windows First Operations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the entire MVP operable from Windows without depending on WSL.

**Architecture:** Keep `apps/web` and `apps/api` running natively on Windows, and standardize infrastructure on Docker Desktop for Windows. Wrap the common workflows in PowerShell so setup, migrations, live checks, and Feishu callback prep all share one Windows-first path.

**Tech Stack:** PowerShell, Docker Desktop, FastAPI, Alembic, Next.js, PostgreSQL, Redis, Qdrant

---

### Task 1: Add Windows workflow scripts

**Files:**
- Create: `scripts/windows/Common.ps1`
- Create: `scripts/windows/Invoke-AgentDoctor.ps1`
- Create: `scripts/windows/Start-AgentInfra.ps1`
- Create: `scripts/windows/Stop-AgentInfra.ps1`
- Create: `scripts/windows/Invoke-AgentMigrate.ps1`
- Create: `scripts/windows/Start-AgentApi.ps1`
- Create: `scripts/windows/Start-AgentWeb.ps1`
- Create: `scripts/windows/Invoke-DeepSeekLiveCheck.ps1`
- Create: `scripts/windows/Start-AgentTunnel.ps1`
- Create: `scripts/windows/Run-DeepSeekLiveCheck.py`

### Task 2: Expose Windows commands from the repo root

**Files:**
- Modify: `package.json`

### Task 3: Document the Windows-first workflow

**Files:**
- Create: `docs/windows-setup.md`
- Modify: `README.md`

### Task 4: Verify the scripts and docs

**Files:**
- Test: `scripts/windows/*.ps1`
- Test: `apps/api/tests/test_integration.py`

**Verification:**
- Parse all PowerShell scripts successfully
- Run the existing backend tests
- Run `npm.cmd run build:web`
