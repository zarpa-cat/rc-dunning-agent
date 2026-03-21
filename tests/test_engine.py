from datetime import datetime, timedelta, timezone

from rc_dunning_agent.models import DunningRecord, DunningStatus
from rc_dunning_agent.store import DunningStore
from rc_dunning_agent.engine import DunningEngine


def _make_engine(tmp_path):
    store = DunningStore(str(tmp_path / "test.db"))
    engine = DunningEngine(store)
    return store, engine


def test_handle_billing_issue_creates_record(tmp_path):
    store, engine = _make_engine(tmp_path)
    record = engine.handle_billing_issue("sub_1", entitlement_id="ent_1", product_id="prod_1")

    assert record.subscriber_id == "sub_1"
    assert record.status == DunningStatus.BILLING_ISSUE
    assert record.entitlement_id == "ent_1"
    assert record.product_id == "prod_1"

    persisted = store.get("sub_1")
    assert persisted is not None
    assert persisted.status == DunningStatus.BILLING_ISSUE


def test_handle_billing_issue_idempotent(tmp_path):
    store, engine = _make_engine(tmp_path)
    first = engine.handle_billing_issue("sub_1")
    second = engine.handle_billing_issue("sub_1")

    assert first.billing_issue_at == second.billing_issue_at
    assert second.status == DunningStatus.BILLING_ISSUE


def test_handle_billing_issue_after_recovery(tmp_path):
    store, engine = _make_engine(tmp_path)
    engine.handle_billing_issue("sub_1")
    engine.handle_renewal("sub_1")

    recovered = store.get("sub_1")
    assert recovered.status == DunningStatus.RECOVERED

    new_record = engine.handle_billing_issue("sub_1")
    assert new_record.status == DunningStatus.BILLING_ISSUE
    assert new_record.billing_issue_at > recovered.billing_issue_at


def test_handle_renewal_marks_recovered(tmp_path):
    store, engine = _make_engine(tmp_path)
    engine.handle_billing_issue("sub_1")

    result = engine.handle_renewal("sub_1")
    assert result is not None
    assert result.status == DunningStatus.RECOVERED
    assert result.recovery_at is not None


def test_handle_renewal_unknown(tmp_path):
    _store, engine = _make_engine(tmp_path)
    result = engine.handle_renewal("unknown_sub")
    assert result is None


def test_handle_expiration_marks_churned(tmp_path):
    store, engine = _make_engine(tmp_path)
    engine.handle_billing_issue("sub_1")

    result = engine.handle_expiration("sub_1")
    assert result is not None
    assert result.status == DunningStatus.CHURNED


def test_handle_expiration_unknown(tmp_path):
    _store, engine = _make_engine(tmp_path)
    result = engine.handle_expiration("unknown_sub")
    assert result is None


def test_process_pending_first_nudge(tmp_path):
    store, engine = _make_engine(tmp_path)
    billing_time = datetime.now(timezone.utc) - timedelta(hours=25)
    record = DunningRecord(
        subscriber_id="sub_1",
        status=DunningStatus.BILLING_ISSUE,
        billing_issue_at=billing_time,
    )
    store.upsert(record)

    now = datetime.now(timezone.utc)
    actions = engine.process_pending(now=now)

    assert len(actions) == 1
    assert actions[0]["subscriber_id"] == "sub_1"
    assert actions[0]["action"] == "send_first_nudge"
    assert actions[0]["status"] == "first_nudge"

    updated = store.get("sub_1")
    assert updated.status == DunningStatus.FIRST_NUDGE
    assert updated.nudge_count == 1


def test_process_pending_second_nudge(tmp_path):
    store, engine = _make_engine(tmp_path)
    billing_time = datetime.now(timezone.utc) - timedelta(hours=73)
    record = DunningRecord(
        subscriber_id="sub_1",
        status=DunningStatus.FIRST_NUDGE,
        billing_issue_at=billing_time,
        nudge_count=1,
    )
    store.upsert(record)

    now = datetime.now(timezone.utc)
    actions = engine.process_pending(now=now)

    assert len(actions) == 1
    assert actions[0]["action"] == "send_second_nudge"
    assert actions[0]["status"] == "second_nudge"

    updated = store.get("sub_1")
    assert updated.status == DunningStatus.SECOND_NUDGE
    assert updated.nudge_count == 2


def test_process_pending_final_nudge(tmp_path):
    store, engine = _make_engine(tmp_path)
    billing_time = datetime.now(timezone.utc) - timedelta(hours=169)
    record = DunningRecord(
        subscriber_id="sub_1",
        status=DunningStatus.SECOND_NUDGE,
        billing_issue_at=billing_time,
        nudge_count=2,
    )
    store.upsert(record)

    now = datetime.now(timezone.utc)
    actions = engine.process_pending(now=now)

    assert len(actions) == 1
    assert actions[0]["action"] == "send_final_nudge"
    assert actions[0]["status"] == "final_nudge"

    updated = store.get("sub_1")
    assert updated.status == DunningStatus.FINAL_NUDGE
    assert updated.nudge_count == 3


def test_process_pending_churn(tmp_path):
    store, engine = _make_engine(tmp_path)
    billing_time = datetime.now(timezone.utc) - timedelta(hours=217)
    record = DunningRecord(
        subscriber_id="sub_1",
        status=DunningStatus.FINAL_NUDGE,
        billing_issue_at=billing_time,
        nudge_count=3,
    )
    store.upsert(record)

    now = datetime.now(timezone.utc)
    actions = engine.process_pending(now=now)

    assert len(actions) == 1
    assert actions[0]["action"] == "mark_churned"
    assert actions[0]["status"] == "churned"

    updated = store.get("sub_1")
    assert updated.status == DunningStatus.CHURNED


def test_process_pending_no_active(tmp_path):
    _store, engine = _make_engine(tmp_path)
    actions = engine.process_pending()
    assert actions == []


def test_get_stats(tmp_path):
    store, engine = _make_engine(tmp_path)
    engine.handle_billing_issue("sub_1")
    engine.handle_billing_issue("sub_2")
    engine.handle_renewal("sub_1")

    stats = engine.get_stats()
    assert stats["total_issues"] == 2
    assert stats["recovered"] == 1
    assert stats["active"] == 1
