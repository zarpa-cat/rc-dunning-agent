from datetime import datetime, timezone, timedelta

from rc_dunning_agent.models import DunningRecord, DunningStatus
from rc_dunning_agent.store import DunningStore
from rc_dunning_agent.analytics import RecoveryAnalytics


def _make_store(tmp_path):
    return DunningStore(str(tmp_path / "test.db"))


def test_recovery_rate_no_data(tmp_path):
    store = _make_store(tmp_path)
    ra = RecoveryAnalytics(store)
    assert ra.recovery_rate() == 0.0


def test_recovery_rate_all_recovered(tmp_path):
    store = _make_store(tmp_path)
    now = datetime.now(timezone.utc)
    for i in range(3):
        store.upsert(DunningRecord(
            subscriber_id=f"sub_{i}",
            status=DunningStatus.RECOVERED,
            billing_issue_at=now - timedelta(days=5),
            recovery_at=now,
        ))
    ra = RecoveryAnalytics(store)
    assert ra.recovery_rate() == 1.0


def test_recovery_rate_mixed(tmp_path):
    store = _make_store(tmp_path)
    now = datetime.now(timezone.utc)
    # 2 recovered, 1 churned, 1 active (active ignored)
    store.upsert(DunningRecord(
        subscriber_id="r1", status=DunningStatus.RECOVERED,
        billing_issue_at=now - timedelta(days=5), recovery_at=now,
    ))
    store.upsert(DunningRecord(
        subscriber_id="r2", status=DunningStatus.RECOVERED,
        billing_issue_at=now - timedelta(days=3), recovery_at=now,
    ))
    store.upsert(DunningRecord(
        subscriber_id="c1", status=DunningStatus.CHURNED,
        billing_issue_at=now - timedelta(days=10),
    ))
    store.upsert(DunningRecord(
        subscriber_id="a1", status=DunningStatus.BILLING_ISSUE,
        billing_issue_at=now,
    ))
    ra = RecoveryAnalytics(store)
    # 2 / (2 + 1) = 0.6667
    assert abs(ra.recovery_rate() - 2 / 3) < 0.001


def test_avg_days_to_recovery_no_data(tmp_path):
    store = _make_store(tmp_path)
    ra = RecoveryAnalytics(store)
    assert ra.avg_days_to_recovery() == 0.0


def test_avg_days_to_recovery(tmp_path):
    store = _make_store(tmp_path)
    now = datetime.now(timezone.utc)
    # One recovered after 2 days, another after 4 days → avg = 3
    store.upsert(DunningRecord(
        subscriber_id="r1", status=DunningStatus.RECOVERED,
        billing_issue_at=now - timedelta(days=2), recovery_at=now,
    ))
    store.upsert(DunningRecord(
        subscriber_id="r2", status=DunningStatus.RECOVERED,
        billing_issue_at=now - timedelta(days=4), recovery_at=now,
    ))
    ra = RecoveryAnalytics(store)
    assert abs(ra.avg_days_to_recovery() - 3.0) < 0.01


def test_nudge_effectiveness_no_data(tmp_path):
    store = _make_store(tmp_path)
    ra = RecoveryAnalytics(store)
    assert ra.nudge_effectiveness() == {}


def test_nudge_effectiveness(tmp_path):
    store = _make_store(tmp_path)
    now = datetime.now(timezone.utc)
    # nudge_count=1: 2 recovered, 1 churned → 66.7%
    # nudge_count=2: 0 recovered, 1 churned → 0%
    store.upsert(DunningRecord(
        subscriber_id="r1", status=DunningStatus.RECOVERED,
        billing_issue_at=now - timedelta(days=5), recovery_at=now, nudge_count=1,
    ))
    store.upsert(DunningRecord(
        subscriber_id="r2", status=DunningStatus.RECOVERED,
        billing_issue_at=now - timedelta(days=3), recovery_at=now, nudge_count=1,
    ))
    store.upsert(DunningRecord(
        subscriber_id="c1", status=DunningStatus.CHURNED,
        billing_issue_at=now - timedelta(days=10), nudge_count=1,
    ))
    store.upsert(DunningRecord(
        subscriber_id="c2", status=DunningStatus.CHURNED,
        billing_issue_at=now - timedelta(days=10), nudge_count=2,
    ))
    ra = RecoveryAnalytics(store)
    ne = ra.nudge_effectiveness()
    assert abs(ne[1] - 2 / 3) < 0.001
    assert ne[2] == 0.0


def test_summary_returns_all_keys(tmp_path):
    store = _make_store(tmp_path)
    ra = RecoveryAnalytics(store)
    s = ra.summary()
    assert "recovery_rate" in s
    assert "avg_days_to_recovery" in s
    assert "nudge_effectiveness" in s


def test_summary_with_data(tmp_path):
    store = _make_store(tmp_path)
    now = datetime.now(timezone.utc)
    store.upsert(DunningRecord(
        subscriber_id="r1", status=DunningStatus.RECOVERED,
        billing_issue_at=now - timedelta(days=2), recovery_at=now, nudge_count=1,
    ))
    store.upsert(DunningRecord(
        subscriber_id="c1", status=DunningStatus.CHURNED,
        billing_issue_at=now - timedelta(days=10), nudge_count=2,
    ))
    ra = RecoveryAnalytics(store)
    s = ra.summary()
    assert s["recovery_rate"] == 0.5
    assert s["avg_days_to_recovery"] > 0
    assert 1 in s["nudge_effectiveness"]
    assert 2 in s["nudge_effectiveness"]


def test_recovery_rate_all_churned(tmp_path):
    store = _make_store(tmp_path)
    now = datetime.now(timezone.utc)
    store.upsert(DunningRecord(
        subscriber_id="c1", status=DunningStatus.CHURNED,
        billing_issue_at=now - timedelta(days=10),
    ))
    ra = RecoveryAnalytics(store)
    assert ra.recovery_rate() == 0.0
