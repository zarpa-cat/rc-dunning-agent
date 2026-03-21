from datetime import datetime, timezone

import pytest

from rc_dunning_agent.models import DunningRecord, DunningStatus
from rc_dunning_agent.store import DunningStore


def _make_record(
    subscriber_id: str = "sub_001",
    status: DunningStatus = DunningStatus.BILLING_ISSUE,
    **kwargs,
) -> DunningRecord:
    defaults = {
        "billing_issue_at": datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        "last_action_at": None,
        "recovery_at": None,
        "nudge_count": 0,
        "entitlement_id": None,
        "product_id": None,
        "notes": "",
    }
    defaults.update(kwargs)
    return DunningRecord(
        subscriber_id=subscriber_id,
        status=status,
        **defaults,
    )


def _make_store(tmp_path) -> DunningStore:
    return DunningStore(db_path=str(tmp_path / "dunning.db"))


def test_upsert_and_get(tmp_path):
    store = _make_store(tmp_path)
    record = _make_record(
        subscriber_id="sub_100",
        status=DunningStatus.FIRST_NUDGE,
        billing_issue_at=datetime(2026, 2, 1, 8, 30, 0, tzinfo=timezone.utc),
        last_action_at=datetime(2026, 2, 2, 10, 0, 0, tzinfo=timezone.utc),
        nudge_count=1,
        entitlement_id="ent_abc",
        product_id="prod_xyz",
        notes="first attempt",
    )
    store.upsert(record)

    fetched = store.get("sub_100")
    assert fetched is not None
    assert fetched.subscriber_id == "sub_100"
    assert fetched.status == DunningStatus.FIRST_NUDGE
    assert fetched.billing_issue_at == datetime(2026, 2, 1, 8, 30, 0, tzinfo=timezone.utc)
    assert fetched.last_action_at == datetime(2026, 2, 2, 10, 0, 0, tzinfo=timezone.utc)
    assert fetched.recovery_at is None
    assert fetched.nudge_count == 1
    assert fetched.entitlement_id == "ent_abc"
    assert fetched.product_id == "prod_xyz"
    assert fetched.notes == "first attempt"


def test_get_missing(tmp_path):
    store = _make_store(tmp_path)
    assert store.get("nonexistent") is None


def test_upsert_update(tmp_path):
    store = _make_store(tmp_path)
    record = _make_record(subscriber_id="sub_200", nudge_count=0)
    store.upsert(record)

    updated = _make_record(
        subscriber_id="sub_200",
        status=DunningStatus.SECOND_NUDGE,
        nudge_count=2,
        last_action_at=datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    store.upsert(updated)

    fetched = store.get("sub_200")
    assert fetched is not None
    assert fetched.status == DunningStatus.SECOND_NUDGE
    assert fetched.nudge_count == 2
    assert fetched.last_action_at == datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_list_by_status(tmp_path):
    store = _make_store(tmp_path)
    store.upsert(_make_record(subscriber_id="sub_a", status=DunningStatus.BILLING_ISSUE))
    store.upsert(_make_record(subscriber_id="sub_b", status=DunningStatus.BILLING_ISSUE))
    store.upsert(_make_record(subscriber_id="sub_c", status=DunningStatus.FIRST_NUDGE))
    store.upsert(_make_record(subscriber_id="sub_d", status=DunningStatus.RECOVERED))

    billing = store.list_by_status(DunningStatus.BILLING_ISSUE)
    assert len(billing) == 2
    assert {r.subscriber_id for r in billing} == {"sub_a", "sub_b"}

    nudge = store.list_by_status(DunningStatus.FIRST_NUDGE)
    assert len(nudge) == 1
    assert nudge[0].subscriber_id == "sub_c"

    recovered = store.list_by_status(DunningStatus.RECOVERED)
    assert len(recovered) == 1

    final = store.list_by_status(DunningStatus.FINAL_NUDGE)
    assert len(final) == 0


def test_list_all_active(tmp_path):
    store = _make_store(tmp_path)
    store.upsert(_make_record(subscriber_id="sub_1", status=DunningStatus.BILLING_ISSUE))
    store.upsert(_make_record(subscriber_id="sub_2", status=DunningStatus.FIRST_NUDGE))
    store.upsert(_make_record(subscriber_id="sub_3", status=DunningStatus.GRACE_PERIOD))
    store.upsert(_make_record(subscriber_id="sub_4", status=DunningStatus.RECOVERED))
    store.upsert(_make_record(subscriber_id="sub_5", status=DunningStatus.CHURNED))

    active = store.list_all_active()
    active_ids = {r.subscriber_id for r in active}
    assert active_ids == {"sub_1", "sub_2", "sub_3"}


def test_mark_recovered(tmp_path):
    store = _make_store(tmp_path)
    store.upsert(_make_record(subscriber_id="sub_rec", status=DunningStatus.SECOND_NUDGE))

    store.mark_recovered("sub_rec")

    fetched = store.get("sub_rec")
    assert fetched is not None
    assert fetched.status == DunningStatus.RECOVERED
    assert fetched.recovery_at is not None
    assert isinstance(fetched.recovery_at, datetime)


def test_mark_churned(tmp_path):
    store = _make_store(tmp_path)
    store.upsert(_make_record(subscriber_id="sub_churn", status=DunningStatus.FINAL_NUDGE))

    store.mark_churned("sub_churn")

    fetched = store.get("sub_churn")
    assert fetched is not None
    assert fetched.status == DunningStatus.CHURNED


def test_recovery_stats(tmp_path):
    store = _make_store(tmp_path)
    store.upsert(_make_record(subscriber_id="sub_1", status=DunningStatus.BILLING_ISSUE))
    store.upsert(_make_record(subscriber_id="sub_2", status=DunningStatus.FIRST_NUDGE))
    store.upsert(_make_record(subscriber_id="sub_3", status=DunningStatus.RECOVERED))
    store.upsert(_make_record(subscriber_id="sub_4", status=DunningStatus.RECOVERED))
    store.upsert(_make_record(subscriber_id="sub_5", status=DunningStatus.CHURNED))

    stats = store.recovery_stats()
    assert stats["total_issues"] == 5
    assert stats["recovered"] == 2
    assert stats["churned"] == 1
    assert stats["active"] == 2
    assert stats["recovery_rate"] == pytest.approx(0.4)


def test_recovery_stats_empty(tmp_path):
    store = _make_store(tmp_path)
    stats = store.recovery_stats()
    assert stats["total_issues"] == 0
    assert stats["recovered"] == 0
    assert stats["churned"] == 0
    assert stats["active"] == 0
    assert stats["recovery_rate"] == 0.0


def test_upsert_preserves_other_fields(tmp_path):
    store = _make_store(tmp_path)
    record = _make_record(
        subscriber_id="sub_preserve",
        status=DunningStatus.BILLING_ISSUE,
        entitlement_id="ent_keep",
        product_id="prod_keep",
        notes="important note",
    )
    store.upsert(record)

    # Update status and nudge_count but keep other fields
    updated = _make_record(
        subscriber_id="sub_preserve",
        status=DunningStatus.FIRST_NUDGE,
        entitlement_id="ent_keep",
        product_id="prod_keep",
        notes="important note",
        nudge_count=1,
        last_action_at=datetime(2026, 3, 10, 9, 0, 0, tzinfo=timezone.utc),
    )
    store.upsert(updated)

    fetched = store.get("sub_preserve")
    assert fetched is not None
    assert fetched.status == DunningStatus.FIRST_NUDGE
    assert fetched.nudge_count == 1
    assert fetched.entitlement_id == "ent_keep"
    assert fetched.product_id == "prod_keep"
    assert fetched.notes == "important note"
