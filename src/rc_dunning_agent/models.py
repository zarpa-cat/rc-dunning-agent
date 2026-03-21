from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class DunningStatus(str, Enum):
    BILLING_ISSUE = "billing_issue"
    FIRST_NUDGE = "first_nudge"
    SECOND_NUDGE = "second_nudge"
    FINAL_NUDGE = "final_nudge"
    RECOVERED = "recovered"
    CHURNED = "churned"
    GRACE_PERIOD = "grace_period"


@dataclass
class DunningRecord:
    subscriber_id: str
    status: DunningStatus
    billing_issue_at: datetime
    last_action_at: Optional[datetime] = None
    recovery_at: Optional[datetime] = None
    nudge_count: int = 0
    entitlement_id: Optional[str] = None
    product_id: Optional[str] = None
    notes: str = ""
