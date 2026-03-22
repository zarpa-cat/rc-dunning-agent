from dataclasses import dataclass


@dataclass
class DunningTemplate:
    subject: str
    body: str

    def render(self, **kwargs: str) -> tuple[str, str]:
        """Render subject and body with provided placeholder values."""
        return self.subject.format(**kwargs), self.body.format(**kwargs)


FIRST_NUDGE = DunningTemplate(
    subject="Action required: update your payment method",
    body=(
        "Hi {subscriber_id},\n\n"
        "We noticed a billing issue with your subscription. "
        "It's been {days_overdue} day(s) since the issue started "
        "(expiry date: {expiry_date}).\n\n"
        "Please update your payment method to continue your subscription.\n\n"
        "Thanks,\nThe Team"
    ),
)

SECOND_NUDGE = DunningTemplate(
    subject="Reminder: your subscription payment failed",
    body=(
        "Hi {subscriber_id},\n\n"
        "This is a friendly reminder that your payment is still failing. "
        "It's been {days_overdue} day(s) since the billing issue was detected "
        "(expiry date: {expiry_date}).\n\n"
        "Please update your payment details to avoid losing access.\n\n"
        "Thanks,\nThe Team"
    ),
)

FINAL_NOTICE = DunningTemplate(
    subject="Final notice: your subscription is about to expire",
    body=(
        "Hi {subscriber_id},\n\n"
        "This is your final notice. Your payment has been failing for "
        "{days_overdue} day(s) and your subscription will expire on {expiry_date}.\n\n"
        "Please update your payment method immediately to keep your access.\n\n"
        "Thanks,\nThe Team"
    ),
)
