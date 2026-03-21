from datetime import datetime, timedelta, timezone

from typer.testing import CliRunner

from rc_dunning_agent.cli import app
from rc_dunning_agent.engine import DunningEngine
from rc_dunning_agent.models import DunningRecord, DunningStatus
from rc_dunning_agent.store import DunningStore

runner = CliRunner()


def _db(tmp_path) -> str:
    return str(tmp_path / "test.db")


def test_list_empty(tmp_path):
    result = runner.invoke(app, ["list", "--db-path", _db(tmp_path)])
    assert result.exit_code == 0
    assert "No active dunning records" in result.output


def test_list_with_records(tmp_path):
    db_path = _db(tmp_path)
    engine = DunningEngine(DunningStore(db_path))
    engine.handle_billing_issue("sub_123")
    engine.handle_billing_issue("sub_456")

    result = runner.invoke(app, ["list", "--db-path", db_path])
    assert result.exit_code == 0
    assert "sub_123" in result.output
    assert "sub_456" in result.output
    assert "billing_issue" in result.output


def test_stats_empty(tmp_path):
    result = runner.invoke(app, ["stats", "--db-path", _db(tmp_path)])
    assert result.exit_code == 0
    assert "Total issues: 0" in result.output
    assert "Recovered: 0" in result.output
    assert "Churned: 0" in result.output
    assert "Active: 0" in result.output
    assert "Recovery rate: 0.0%" in result.output


def test_stats_with_data(tmp_path):
    db_path = _db(tmp_path)
    store = DunningStore(db_path)
    engine = DunningEngine(store)
    engine.handle_billing_issue("sub_1")
    engine.handle_billing_issue("sub_2")
    engine.handle_billing_issue("sub_3")
    store.mark_recovered("sub_1")
    store.mark_churned("sub_2")

    result = runner.invoke(app, ["stats", "--db-path", db_path])
    assert result.exit_code == 0
    assert "Total issues: 3" in result.output
    assert "Recovered: 1" in result.output
    assert "Churned: 1" in result.output
    assert "Active: 1" in result.output
    assert "Recovery rate: 33.3%" in result.output


def test_mark_recovered(tmp_path):
    db_path = _db(tmp_path)
    engine = DunningEngine(DunningStore(db_path))
    engine.handle_billing_issue("sub_abc")

    result = runner.invoke(app, ["mark-recovered", "sub_abc", "--db-path", db_path])
    assert result.exit_code == 0
    assert "Marked sub_abc as recovered" in result.output

    store = DunningStore(db_path)
    record = store.get("sub_abc")
    assert record.status == DunningStatus.RECOVERED


def test_mark_recovered_unknown(tmp_path):
    result = runner.invoke(app, ["mark-recovered", "sub_unknown", "--db-path", _db(tmp_path)])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_mark_churned(tmp_path):
    db_path = _db(tmp_path)
    engine = DunningEngine(DunningStore(db_path))
    engine.handle_billing_issue("sub_xyz")

    result = runner.invoke(app, ["mark-churned", "sub_xyz", "--db-path", db_path])
    assert result.exit_code == 0
    assert "Marked sub_xyz as churned" in result.output

    store = DunningStore(db_path)
    record = store.get("sub_xyz")
    assert record.status == DunningStatus.CHURNED


def test_mark_churned_unknown(tmp_path):
    result = runner.invoke(app, ["mark-churned", "sub_unknown", "--db-path", _db(tmp_path)])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_process_no_actions(tmp_path):
    result = runner.invoke(app, ["process", "--db-path", _db(tmp_path)])
    assert result.exit_code == 0
    assert "No actions taken" in result.output


def test_process_with_actions(tmp_path):
    db_path = _db(tmp_path)
    store = DunningStore(db_path)
    # Create a record with billing_issue_at set 25 hours in the past
    now = datetime.now(timezone.utc)
    record = DunningRecord(
        subscriber_id="sub_stale",
        status=DunningStatus.BILLING_ISSUE,
        billing_issue_at=now - timedelta(hours=25),
    )
    store.upsert(record)

    result = runner.invoke(app, ["process", "--db-path", db_path])
    assert result.exit_code == 0
    assert "sub_stale" in result.output
    assert "send_first_nudge" in result.output
    assert "first_nudge" in result.output


def test_add(tmp_path):
    db_path = _db(tmp_path)
    result = runner.invoke(app, ["add", "sub_new", "--db-path", db_path])
    assert result.exit_code == 0
    assert "Added billing issue for sub_new" in result.output
    assert "billing_issue" in result.output

    store = DunningStore(db_path)
    record = store.get("sub_new")
    assert record is not None
    assert record.status == DunningStatus.BILLING_ISSUE
