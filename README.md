# rc-dunning-agent

Automated payment recovery (dunning) manager for RevenueCat. Tracks billing failures, implements configurable dunning schedules, and records recovery outcomes.

## Install

```bash
uv sync
```

## Usage

### CLI (`rda`)

```bash
# Add a billing issue manually (for testing)
rda add sub_12345

# List all active dunning records
rda list

# Run the dunning processor (sends nudges, marks churned)
rda process

# View recovery statistics
rda stats

# Manually mark a subscriber
rda mark-recovered sub_12345
rda mark-churned sub_12345
```

All commands accept `--db-path` to specify a custom SQLite database location (default: `./dunning.db`).

### Webhook Integration

Route RevenueCat webhook events to the `RCWebhookHandler`:

```python
from rc_dunning_agent.store import DunningStore
from rc_dunning_agent.engine import DunningEngine
from rc_dunning_agent.webhook import RCWebhookHandler

store = DunningStore("./dunning.db")
engine = DunningEngine(store)
handler = RCWebhookHandler(engine, auth_key="your-rc-webhook-secret")

# In your webhook endpoint:
result = handler.handle(payload, auth_header=request.headers.get("Authorization"))
```

### Dunning Schedule

Default schedule (configurable):

| Action | Timing |
|--------|--------|
| First nudge | 24 hours after billing issue |
| Second nudge | 72 hours (3 days) |
| Final nudge | 168 hours (7 days) |
| Mark churned | 216 hours (9 days) |

```python
from rc_dunning_agent.schedule import DunningSchedule

custom = DunningSchedule(
    first_nudge_hours=12,
    second_nudge_hours=48,
    final_nudge_hours=120,
    churn_after_hours=168,
)
engine = DunningEngine(store, schedule=custom)
```

## Development

```bash
uv run pytest -v        # Run tests
uv run ruff check src/ tests/  # Lint
```
