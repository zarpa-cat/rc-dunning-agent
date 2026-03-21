# Phase 1: RC Dunning Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated payment recovery (dunning) manager for RevenueCat that tracks billing failures, implements configurable dunning schedules, and records recovery outcomes.

**Architecture:** SQLite-backed store with a dunning engine that processes billing events from RevenueCat webhooks. A CLI (`rda`) provides manual management. Core flow: webhook event → engine → store → schedule-based nudge actions.

**Tech Stack:** Python 3.11+, sqlite3 (stdlib), pydantic>=2, httpx, typer, rich, click, pytest, pytest-asyncio, ruff

---

### Task 1: Project Setup

**Files:**
- Create: `pyproject.toml` (via `uv init`)
- Create: `src/rc_dunning_agent/__init__.py`

- [ ] **Step 1: Initialize project with uv**

```bash
uv init --no-readme
```

- [ ] **Step 2: Configure pyproject.toml**

Set package name to `rc_dunning_agent`, src layout, add all dependencies, ruff config, and CLI entry point.

```toml
[project]
name = "rc-dunning-agent"
version = "0.1.0"
description = "Automated payment recovery / dunning manager for RevenueCat"
requires-python = ">=3.11"
dependencies = [
    "httpx",
    "pydantic>=2",
    "typer",
    "rich",
    "click",
]

[dependency-groups]
dev = [
    "pytest",
    "pytest-asyncio",
    "ruff",
]

[project.scripts]
rda = "rc_dunning_agent.cli:app"

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 3: Create src layout**

```bash
mkdir -p src/rc_dunning_agent
touch src/rc_dunning_agent/__init__.py
mkdir -p tests
touch tests/__init__.py
```

- [ ] **Step 4: Install dependencies**

```bash
uv sync
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "chore: project setup with uv, dependencies, src layout"
```

---

### Task 2: Models

**Files:**
- Create: `src/rc_dunning_agent/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write tests for models**

```python
# tests/test_models.py
from datetime import datetime
from rc_dunning_agent.models import DunningStatus, DunningRecord

def test_dunning_status_values():
    assert DunningStatus.BILLING_ISSUE == "billing_issue"
    assert DunningStatus.RECOVERED == "recovered"
    assert DunningStatus.CHURNED == "churned"

def test_dunning_record_defaults():
    rec = DunningRecord(
        subscriber_id="sub_1",
        status=DunningStatus.BILLING_ISSUE,
        billing_issue_at=datetime(2026, 1, 1),
    )
    assert rec.nudge_count == 0
    assert rec.last_action_at is None
    assert rec.recovery_at is None
    assert rec.notes == ""

def test_dunning_record_full():
    now = datetime.now()
    rec = DunningRecord(
        subscriber_id="sub_2",
        status=DunningStatus.FIRST_NUDGE,
        billing_issue_at=now,
        last_action_at=now,
        recovery_at=None,
        nudge_count=1,
        entitlement_id="ent_1",
        product_id="prod_1",
        notes="test note",
    )
    assert rec.subscriber_id == "sub_2"
    assert rec.entitlement_id == "ent_1"
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
uv run pytest tests/test_models.py -v
```

- [ ] **Step 3: Implement models**

Create `src/rc_dunning_agent/models.py` with `DunningStatus` enum and `DunningRecord` dataclass per spec.

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/rc_dunning_agent/models.py tests/test_models.py
git commit -m "feat: add DunningStatus enum and DunningRecord dataclass"
```

---

### Task 3: DunningStore

**Files:**
- Create: `src/rc_dunning_agent/store.py`
- Create: `tests/test_store.py`

- [ ] **Step 1: Write tests for store CRUD + analytics**

Tests should cover: upsert new record, upsert update, get existing, get missing, list_by_status, list_all_active (excludes RECOVERED/CHURNED), mark_recovered, mark_churned, recovery_stats.

Use `tmp_path` fixture for isolated DB per test.

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement DunningStore**

SQLite-backed with raw `sqlite3`. Table schema:
```sql
CREATE TABLE IF NOT EXISTS dunning_records (
    subscriber_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    billing_issue_at TEXT NOT NULL,
    last_action_at TEXT,
    recovery_at TEXT,
    nudge_count INTEGER DEFAULT 0,
    entitlement_id TEXT,
    product_id TEXT,
    notes TEXT DEFAULT ''
)
```

Serialize datetimes as ISO format strings. Deserialize back to `datetime` objects.

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/rc_dunning_agent/store.py tests/test_store.py
git commit -m "feat: add SQLite-backed DunningStore with CRUD and analytics"
```

---

### Task 4: DunningSchedule

**Files:**
- Create: `src/rc_dunning_agent/schedule.py`
- Create: `tests/test_schedule.py`

- [ ] **Step 1: Write tests for schedule action determination**

Test boundary cases: just before and just after each threshold (24h, 72h, 168h, 216h). Test each status transition. Test NO_ACTION for already-nudged-recently cases.

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement DunningSchedule and determine_action**

Logic: compare hours since `billing_issue_at` against schedule thresholds, considering current `status` and `nudge_count` to determine next action.

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/rc_dunning_agent/schedule.py tests/test_schedule.py
git commit -m "feat: add DunningSchedule with configurable nudge timing"
```

---

### Task 5: DunningEngine

**Files:**
- Create: `src/rc_dunning_agent/engine.py`
- Create: `tests/test_engine.py`

- [ ] **Step 1: Write tests for engine**

Test: handle_billing_issue creates record, handle_billing_issue idempotent, handle_renewal marks recovered, handle_renewal for unknown subscriber returns None, handle_expiration marks churned, process_pending fires correct actions at correct times, process_pending with no active records, get_stats delegates to store.

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement DunningEngine**

Engine orchestrates store + schedule. `process_pending` iterates all active records, calls `determine_action`, updates records accordingly, returns action log.

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/rc_dunning_agent/engine.py tests/test_engine.py
git commit -m "feat: add DunningEngine with billing issue, renewal, expiration handling"
```

---

### Task 6: Webhook Handler

**Files:**
- Create: `src/rc_dunning_agent/webhook.py`
- Create: `tests/test_webhook.py`

- [ ] **Step 1: Write tests for webhook**

Test: parse_rc_event extracts event_type and subscriber_id, handle routes BILLING_ISSUE/RENEWAL/EXPIRATION/UNCANCELLATION/CANCELLATION correctly, handle with auth_key validates header, handle rejects bad auth, handle ignores INITIAL_PURCHASE gracefully.

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement webhook handler**

`parse_rc_event` extracts from `payload["event"]["type"]` and `payload["event"]["app_user_id"]`. `RCWebhookHandler.handle` routes events to appropriate engine methods.

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/rc_dunning_agent/webhook.py tests/test_webhook.py
git commit -m "feat: add RevenueCat webhook handler with auth verification"
```

---

### Task 7: CLI

**Files:**
- Create: `src/rc_dunning_agent/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write tests for CLI commands**

Use `typer.testing.CliRunner`. Test: `list` shows active records, `stats` shows recovery stats, `mark-recovered` updates record, `mark-churned` updates record, `process` runs pending actions, `add` creates billing issue record.

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement CLI**

Typer app with rich table output. Each command instantiates `DunningStore` and `DunningEngine` with default DB path.

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/rc_dunning_agent/cli.py tests/test_cli.py
git commit -m "feat: add rda CLI with list, stats, process, mark, add commands"
```

---

### Task 8: Final Verification & README

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest -v
```

Expect: 40+ tests, all passing.

- [ ] **Step 2: Run ruff**

```bash
uv run ruff check src/ tests/
```

Expect: clean, no errors.

- [ ] **Step 3: Write README.md**

Install/usage/example documentation.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: Phase 1 — DunningEngine, DunningStore, schedule, webhook handler, CLI (N tests)"
```

- [ ] **Step 5: Ship event**

```bash
openclaw system event --text "Done: rc-dunning-agent Phase 1 shipped — DunningEngine, DunningStore, schedule, webhook handler, CLI" --mode now
```
