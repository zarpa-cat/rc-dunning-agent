from datetime import datetime, timedelta

from rc_dunning_agent.models import DunningStatus, DunningRecord
from rc_dunning_agent.schedule import DunningAction, DunningSchedule, determine_action


def _make_record(status: DunningStatus, hours_ago: float, now: datetime) -> DunningRecord:
    return DunningRecord(
        subscriber_id="sub_test",
        status=status,
        billing_issue_at=now - timedelta(hours=hours_ago),
    )


def test_no_action_just_created():
    now = datetime(2026, 1, 1)
    record = _make_record(DunningStatus.BILLING_ISSUE, 0, now)
    assert determine_action(record, DunningSchedule(), now) == DunningAction.NO_ACTION


def test_first_nudge_at_threshold():
    now = datetime(2026, 1, 1)
    record = _make_record(DunningStatus.BILLING_ISSUE, 24, now)
    assert determine_action(record, DunningSchedule(), now) == DunningAction.SEND_FIRST_NUDGE


def test_no_first_nudge_before_threshold():
    now = datetime(2026, 1, 1)
    record = _make_record(DunningStatus.BILLING_ISSUE, 23 + 59 / 60, now)
    assert determine_action(record, DunningSchedule(), now) == DunningAction.NO_ACTION


def test_first_nudge_after_threshold():
    now = datetime(2026, 1, 1)
    record = _make_record(DunningStatus.BILLING_ISSUE, 25, now)
    assert determine_action(record, DunningSchedule(), now) == DunningAction.SEND_FIRST_NUDGE


def test_second_nudge_at_threshold():
    now = datetime(2026, 1, 1)
    record = _make_record(DunningStatus.FIRST_NUDGE, 72, now)
    assert determine_action(record, DunningSchedule(), now) == DunningAction.SEND_SECOND_NUDGE


def test_no_second_nudge_before_threshold():
    now = datetime(2026, 1, 1)
    record = _make_record(DunningStatus.FIRST_NUDGE, 71, now)
    assert determine_action(record, DunningSchedule(), now) == DunningAction.NO_ACTION


def test_final_nudge_at_threshold():
    now = datetime(2026, 1, 1)
    record = _make_record(DunningStatus.SECOND_NUDGE, 168, now)
    assert determine_action(record, DunningSchedule(), now) == DunningAction.SEND_FINAL_NUDGE


def test_no_final_nudge_before_threshold():
    now = datetime(2026, 1, 1)
    record = _make_record(DunningStatus.SECOND_NUDGE, 167, now)
    assert determine_action(record, DunningSchedule(), now) == DunningAction.NO_ACTION


def test_churn_at_threshold():
    now = datetime(2026, 1, 1)
    record = _make_record(DunningStatus.FINAL_NUDGE, 216, now)
    assert determine_action(record, DunningSchedule(), now) == DunningAction.MARK_CHURNED


def test_no_churn_before_threshold():
    now = datetime(2026, 1, 1)
    record = _make_record(DunningStatus.FINAL_NUDGE, 215, now)
    assert determine_action(record, DunningSchedule(), now) == DunningAction.NO_ACTION


def test_no_action_recovered():
    now = datetime(2026, 1, 1)
    record = _make_record(DunningStatus.RECOVERED, 500, now)
    assert determine_action(record, DunningSchedule(), now) == DunningAction.NO_ACTION


def test_no_action_churned():
    now = datetime(2026, 1, 1)
    record = _make_record(DunningStatus.CHURNED, 500, now)
    assert determine_action(record, DunningSchedule(), now) == DunningAction.NO_ACTION


def test_custom_schedule():
    now = datetime(2026, 1, 1)
    schedule = DunningSchedule(
        first_nudge_hours=12,
        second_nudge_hours=36,
        final_nudge_hours=84,
        churn_after_hours=120,
    )
    # 12 hours should trigger first nudge with custom schedule
    record = _make_record(DunningStatus.BILLING_ISSUE, 12, now)
    assert determine_action(record, schedule, now) == DunningAction.SEND_FIRST_NUDGE

    # 11 hours should not trigger with custom schedule
    record = _make_record(DunningStatus.BILLING_ISSUE, 11, now)
    assert determine_action(record, schedule, now) == DunningAction.NO_ACTION

    # 36 hours should trigger second nudge with custom schedule
    record = _make_record(DunningStatus.FIRST_NUDGE, 36, now)
    assert determine_action(record, schedule, now) == DunningAction.SEND_SECOND_NUDGE

    # 84 hours should trigger final nudge with custom schedule
    record = _make_record(DunningStatus.SECOND_NUDGE, 84, now)
    assert determine_action(record, schedule, now) == DunningAction.SEND_FINAL_NUDGE

    # 120 hours should trigger churn with custom schedule
    record = _make_record(DunningStatus.FINAL_NUDGE, 120, now)
    assert determine_action(record, schedule, now) == DunningAction.MARK_CHURNED


def test_churn_overrides_nudge():
    now = datetime(2026, 1, 1)
    # At 216+ hours, even BILLING_ISSUE status should result in MARK_CHURNED
    record = _make_record(DunningStatus.BILLING_ISSUE, 216, now)
    assert determine_action(record, DunningSchedule(), now) == DunningAction.MARK_CHURNED

    record = _make_record(DunningStatus.BILLING_ISSUE, 300, now)
    assert determine_action(record, DunningSchedule(), now) == DunningAction.MARK_CHURNED
