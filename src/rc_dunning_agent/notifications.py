from dataclasses import dataclass

import httpx

from rc_dunning_agent.templates import DunningTemplate


@dataclass
class ResendConfig:
    api_key: str
    from_email: str


@dataclass
class SlackConfig:
    webhook_url: str


class NotificationService:
    def __init__(
        self,
        resend_config: ResendConfig | None = None,
        slack_config: SlackConfig | None = None,
    ):
        self.resend_config = resend_config
        self.slack_config = slack_config

    def send_email(
        self,
        subscriber_id: str,
        template: DunningTemplate,
        to_email: str = "",
        days_overdue: int = 0,
        expiry_date: str = "",
        dry_run: bool = False,
    ) -> dict:
        """Send a recovery nudge email via Resend API."""
        subject, body = template.render(
            subscriber_id=subscriber_id,
            days_overdue=str(days_overdue),
            expiry_date=expiry_date,
        )

        if dry_run:
            return {"status": "dry_run", "subject": subject, "body": body}

        if not self.resend_config:
            raise ValueError("ResendConfig is required to send emails")

        email_to = to_email or f"{subscriber_id}@example.com"

        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {self.resend_config.api_key}"},
            json={
                "from": self.resend_config.from_email,
                "to": [email_to],
                "subject": subject,
                "text": body,
            },
        )
        response.raise_for_status()
        return {"status": "sent", "resend_response": response.json()}

    def send_slack(self, message: str) -> dict:
        """Send a message to Slack via incoming webhook."""
        if not self.slack_config:
            raise ValueError("SlackConfig is required to send Slack messages")

        response = httpx.post(
            self.slack_config.webhook_url,
            json={"text": message},
        )
        response.raise_for_status()
        return {"status": "sent"}
