from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from rc_dunning_agent.models import DunningStatus, DunningRecord


@dataclass
class DunningSchedule:
    first_nudge_hours: int = 24
    second_nudge_hours: int = 72
    final_nudge_hours: int = 168
    churn_after_hours: int = 216


class DunningAction(str, Enum):
    SEND_FIRST_NUDGE = "send_first_nudge"
    SEND_SECOND_NUDGE = "send_second_nudge"
    SEND_FINAL_NUDGE = "send_final_nudge"
    MARK_CHURNED = "mark_churned"
    NO_ACTION = "no_action"


def determine_action(
    record: DunningRecord, schedule: DunningSchedule, now: datetime
) -> DunningAction:
    """Determine the next action for a subscriber based on elapsed time and current status."""
    if record.status in (DunningStatus.RECOVERED, DunningStatus.CHURNED):
        return DunningAction.NO_ACTION

    hours_elapsed = (now - record.billing_issue_at).total_seconds() / 3600

    if hours_elapsed >= schedule.churn_after_hours and record.status in (
        DunningStatus.FINAL_NUDGE,
        DunningStatus.BILLING_ISSUE,
        DunningStatus.FIRST_NUDGE,
        DunningStatus.SECOND_NUDGE,
        DunningStatus.GRACE_PERIOD,
    ):
        return DunningAction.MARK_CHURNED

    if record.status == DunningStatus.BILLING_ISSUE and hours_elapsed >= schedule.first_nudge_hours:
        return DunningAction.SEND_FIRST_NUDGE

    if record.status == DunningStatus.FIRST_NUDGE and hours_elapsed >= schedule.second_nudge_hours:
        return DunningAction.SEND_SECOND_NUDGE

    if record.status == DunningStatus.SECOND_NUDGE and hours_elapsed >= schedule.final_nudge_hours:
        return DunningAction.SEND_FINAL_NUDGE

    return DunningAction.NO_ACTION
