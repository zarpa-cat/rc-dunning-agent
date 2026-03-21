from datetime import datetime, timezone
from typing import Optional

from rc_dunning_agent.models import DunningRecord, DunningStatus
from rc_dunning_agent.store import DunningStore
from rc_dunning_agent.schedule import DunningSchedule, DunningAction, determine_action


class DunningEngine:
    def __init__(self, store: DunningStore, schedule: DunningSchedule = None, notifier=None):
        self.store = store
        self.schedule = schedule or DunningSchedule()
        self.notifier = notifier  # Optional, not used in phase 1

    def handle_billing_issue(
        self, subscriber_id: str, entitlement_id: str = None, product_id: str = None
    ) -> DunningRecord:
        """Called when RC BILLING_ISSUE webhook fires. Creates/updates record."""
        existing = self.store.get(subscriber_id)
        if existing and existing.status not in (DunningStatus.RECOVERED, DunningStatus.CHURNED):
            return existing  # Already tracking this issue

        now = datetime.now(timezone.utc)
        record = DunningRecord(
            subscriber_id=subscriber_id,
            status=DunningStatus.BILLING_ISSUE,
            billing_issue_at=now,
            entitlement_id=entitlement_id,
            product_id=product_id,
        )
        self.store.upsert(record)
        return record

    def handle_renewal(self, subscriber_id: str) -> Optional[DunningRecord]:
        """Called when RC RENEWAL or UNCANCELLATION fires. Marks subscriber recovered."""
        record = self.store.get(subscriber_id)
        if record is None:
            return None
        self.store.mark_recovered(subscriber_id)
        return self.store.get(subscriber_id)

    def handle_expiration(self, subscriber_id: str) -> Optional[DunningRecord]:
        """Called when RC EXPIRATION fires. Marks subscriber churned."""
        record = self.store.get(subscriber_id)
        if record is None:
            return None
        self.store.mark_churned(subscriber_id)
        return self.store.get(subscriber_id)

    def process_pending(self, now: datetime = None) -> list[dict]:
        """Check all active records and fire nudges/updates as needed."""
        if now is None:
            now = datetime.now(timezone.utc)

        actions_taken = []
        for record in self.store.list_all_active():
            action = determine_action(record, self.schedule, now)
            if action == DunningAction.NO_ACTION:
                continue

            if action == DunningAction.MARK_CHURNED:
                self.store.mark_churned(record.subscriber_id)
                actions_taken.append({
                    "subscriber_id": record.subscriber_id,
                    "action": action.value,
                    "status": DunningStatus.CHURNED.value,
                })
            else:
                # Map action to new status
                status_map = {
                    DunningAction.SEND_FIRST_NUDGE: DunningStatus.FIRST_NUDGE,
                    DunningAction.SEND_SECOND_NUDGE: DunningStatus.SECOND_NUDGE,
                    DunningAction.SEND_FINAL_NUDGE: DunningStatus.FINAL_NUDGE,
                }
                new_status = status_map[action]
                record.status = new_status
                record.nudge_count += 1
                record.last_action_at = now
                self.store.upsert(record)
                actions_taken.append({
                    "subscriber_id": record.subscriber_id,
                    "action": action.value,
                    "status": new_status.value,
                })

        return actions_taken

    def get_stats(self) -> dict:
        """Return recovery stats from store."""
        return self.store.recovery_stats()
