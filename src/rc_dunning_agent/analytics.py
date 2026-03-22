from rc_dunning_agent.models import DunningStatus
from rc_dunning_agent.store import DunningStore


class RecoveryAnalytics:
    def __init__(self, store: DunningStore):
        self.store = store

    def recovery_rate(self) -> float:
        """Recovered / (recovered + churned). Returns 0.0 if no terminal records."""
        recovered = len(self.store.list_by_status(DunningStatus.RECOVERED))
        churned = len(self.store.list_by_status(DunningStatus.CHURNED))
        total = recovered + churned
        if total == 0:
            return 0.0
        return recovered / total

    def avg_days_to_recovery(self) -> float:
        """Mean days from billing_issue_at to recovery_at for recovered subscribers."""
        records = self.store.list_by_status(DunningStatus.RECOVERED)
        if not records:
            return 0.0
        days = []
        for r in records:
            if r.recovery_at:
                delta = (r.recovery_at - r.billing_issue_at).total_seconds() / 86400
                days.append(delta)
        if not days:
            return 0.0
        return sum(days) / len(days)

    def nudge_effectiveness(self) -> dict[int, float]:
        """Per nudge_count: recovery rate among subscribers who received that many nudges."""
        recovered = self.store.list_by_status(DunningStatus.RECOVERED)
        churned = self.store.list_by_status(DunningStatus.CHURNED)

        # Group by nudge_count
        nudge_recovered: dict[int, int] = {}
        nudge_total: dict[int, int] = {}

        for r in recovered:
            nudge_recovered[r.nudge_count] = nudge_recovered.get(r.nudge_count, 0) + 1
            nudge_total[r.nudge_count] = nudge_total.get(r.nudge_count, 0) + 1

        for r in churned:
            nudge_total[r.nudge_count] = nudge_total.get(r.nudge_count, 0) + 1

        result: dict[int, float] = {}
        for count, total in sorted(nudge_total.items()):
            rec = nudge_recovered.get(count, 0)
            result[count] = rec / total if total > 0 else 0.0
        return result

    def summary(self) -> dict:
        """All analytics metrics in one call."""
        return {
            "recovery_rate": self.recovery_rate(),
            "avg_days_to_recovery": self.avg_days_to_recovery(),
            "nudge_effectiveness": self.nudge_effectiveness(),
        }
