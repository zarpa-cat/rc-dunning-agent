from rc_dunning_agent.engine import DunningEngine


def parse_rc_event(payload: dict) -> tuple[str, str]:
    """
    Parse RC webhook payload.
    Returns (event_type, subscriber_id).
    RC event types: BILLING_ISSUE, RENEWAL, INITIAL_PURCHASE, UNCANCELLATION, EXPIRATION, CANCELLATION
    subscriber_id is payload["event"]["app_user_id"]
    """
    event = payload.get("event", {})
    event_type = event.get("type", "")
    subscriber_id = event.get("app_user_id", "")
    if not event_type or not subscriber_id:
        raise ValueError("Invalid webhook payload: missing event type or app_user_id")
    return event_type, subscriber_id


class RCWebhookHandler:
    def __init__(self, engine: DunningEngine, auth_key: str = None):
        self.engine = engine
        self.auth_key = auth_key

    def handle(self, payload: dict, auth_header: str = None) -> dict:
        """
        Process an RC webhook payload.
        Returns {"processed": bool, "action": str, "subscriber_id": str}
        Raises ValueError if auth fails.
        """
        if self.auth_key and auth_header != self.auth_key:
            raise ValueError("Webhook authentication failed")

        event_type, subscriber_id = parse_rc_event(payload)

        if event_type == "BILLING_ISSUE":
            # Extract product info from payload if available
            event = payload.get("event", {})
            entitlement_id = event.get("entitlement_ids", [None])[0] if event.get("entitlement_ids") else None
            product_id = event.get("product_id")
            self.engine.handle_billing_issue(subscriber_id, entitlement_id=entitlement_id, product_id=product_id)
            return {"processed": True, "action": "billing_issue_tracked", "subscriber_id": subscriber_id}

        elif event_type in ("RENEWAL", "UNCANCELLATION"):
            result = self.engine.handle_renewal(subscriber_id)
            action = "marked_recovered" if result else "ignored_unknown"
            return {"processed": result is not None, "action": action, "subscriber_id": subscriber_id}

        elif event_type == "EXPIRATION":
            result = self.engine.handle_expiration(subscriber_id)
            action = "marked_churned" if result else "ignored_unknown"
            return {"processed": result is not None, "action": action, "subscriber_id": subscriber_id}

        elif event_type == "CANCELLATION":
            # Cancellation doesn't immediately churn - they might still have active period
            return {"processed": False, "action": "ignored_cancellation", "subscriber_id": subscriber_id}

        else:
            # INITIAL_PURCHASE and other events - not relevant to dunning
            return {"processed": False, "action": "ignored", "subscriber_id": subscriber_id}
