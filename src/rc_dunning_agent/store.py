import sqlite3
from datetime import datetime, timezone
from typing import Optional

from rc_dunning_agent.models import DunningRecord, DunningStatus


class DunningStore:
    def __init__(self, db_path: str = "./dunning.db"):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dunning_records (
                subscriber_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                billing_issue_at TEXT NOT NULL,
                last_action_at TEXT,
                recovery_at TEXT,
                nudge_count INTEGER DEFAULT 0,
                entitlement_id TEXT,
                product_id TEXT,
                notes TEXT DEFAULT ''
            )
            """
        )
        self._conn.commit()

    def _row_to_record(self, row: sqlite3.Row) -> DunningRecord:
        return DunningRecord(
            subscriber_id=row["subscriber_id"],
            status=DunningStatus(row["status"]),
            billing_issue_at=datetime.fromisoformat(row["billing_issue_at"]),
            last_action_at=(
                datetime.fromisoformat(row["last_action_at"])
                if row["last_action_at"]
                else None
            ),
            recovery_at=(
                datetime.fromisoformat(row["recovery_at"])
                if row["recovery_at"]
                else None
            ),
            nudge_count=row["nudge_count"],
            entitlement_id=row["entitlement_id"],
            product_id=row["product_id"],
            notes=row["notes"] or "",
        )

    def upsert(self, record: DunningRecord) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO dunning_records
                (subscriber_id, status, billing_issue_at, last_action_at,
                 recovery_at, nudge_count, entitlement_id, product_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.subscriber_id,
                record.status.value,
                record.billing_issue_at.isoformat(),
                record.last_action_at.isoformat() if record.last_action_at else None,
                record.recovery_at.isoformat() if record.recovery_at else None,
                record.nudge_count,
                record.entitlement_id,
                record.product_id,
                record.notes,
            ),
        )
        self._conn.commit()

    def get(self, subscriber_id: str) -> Optional[DunningRecord]:
        cursor = self._conn.execute(
            "SELECT * FROM dunning_records WHERE subscriber_id = ?",
            (subscriber_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_by_status(self, status: DunningStatus) -> list[DunningRecord]:
        cursor = self._conn.execute(
            "SELECT * FROM dunning_records WHERE status = ?",
            (status.value,),
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def list_all_active(self) -> list[DunningRecord]:
        cursor = self._conn.execute(
            "SELECT * FROM dunning_records WHERE status NOT IN (?, ?)",
            (DunningStatus.RECOVERED.value, DunningStatus.CHURNED.value),
        )
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def mark_recovered(self, subscriber_id: str) -> None:
        now = datetime.now(timezone.utc)
        self._conn.execute(
            """
            UPDATE dunning_records
            SET status = ?, recovery_at = ?
            WHERE subscriber_id = ?
            """,
            (DunningStatus.RECOVERED.value, now.isoformat(), subscriber_id),
        )
        self._conn.commit()

    def mark_churned(self, subscriber_id: str) -> None:
        self._conn.execute(
            "UPDATE dunning_records SET status = ? WHERE subscriber_id = ?",
            (DunningStatus.CHURNED.value, subscriber_id),
        )
        self._conn.commit()

    def recovery_stats(self) -> dict:
        cursor = self._conn.execute(
            "SELECT status, COUNT(*) as cnt FROM dunning_records GROUP BY status"
        )
        counts: dict[str, int] = {}
        for row in cursor.fetchall():
            counts[row["status"]] = row["cnt"]

        total = sum(counts.values())
        recovered = counts.get(DunningStatus.RECOVERED.value, 0)
        churned = counts.get(DunningStatus.CHURNED.value, 0)
        active = total - recovered - churned
        recovery_rate = recovered / total if total > 0 else 0.0

        return {
            "total_issues": total,
            "recovered": recovered,
            "churned": churned,
            "active": active,
            "recovery_rate": recovery_rate,
        }
