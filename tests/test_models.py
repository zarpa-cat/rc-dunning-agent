from datetime import datetime

from rc_dunning_agent.models import DunningStatus, DunningRecord


def test_dunning_status_values():
    assert DunningStatus.BILLING_ISSUE == "billing_issue"
    assert DunningStatus.FIRST_NUDGE == "first_nudge"
    assert DunningStatus.SECOND_NUDGE == "second_nudge"
    assert DunningStatus.FINAL_NUDGE == "final_nudge"
    assert DunningStatus.RECOVERED == "recovered"
    assert DunningStatus.CHURNED == "churned"
    assert DunningStatus.GRACE_PERIOD == "grace_period"


def test_dunning_status_is_str():
    assert isinstance(DunningStatus.BILLING_ISSUE, str)


def test_dunning_record_defaults():
    rec = DunningRecord(
        subscriber_id="sub_1",
        status=DunningStatus.BILLING_ISSUE,
        billing_issue_at=datetime(2026, 1, 1),
    )
    assert rec.nudge_count == 0
    assert rec.last_action_at is None
    assert rec.recovery_at is None
    assert rec.entitlement_id is None
    assert rec.product_id is None
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
    assert rec.status == DunningStatus.FIRST_NUDGE
    assert rec.entitlement_id == "ent_1"
    assert rec.product_id == "prod_1"
    assert rec.notes == "test note"
    assert rec.nudge_count == 1
