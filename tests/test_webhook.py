import pytest

from rc_dunning_agent.engine import DunningEngine
from rc_dunning_agent.store import DunningStore
from rc_dunning_agent.webhook import RCWebhookHandler, parse_rc_event


def _make_engine(tmp_path) -> DunningEngine:
    store = DunningStore(str(tmp_path / "test.db"))
    return DunningEngine(store)


# --- parse_rc_event tests ---


def test_parse_rc_event_valid():
    payload = {"event": {"type": "BILLING_ISSUE", "app_user_id": "sub_123"}}
    event_type, subscriber_id = parse_rc_event(payload)
    assert event_type == "BILLING_ISSUE"
    assert subscriber_id == "sub_123"


def test_parse_rc_event_missing_type():
    payload = {"event": {"app_user_id": "sub_123"}}
    with pytest.raises(ValueError, match="missing event type or app_user_id"):
        parse_rc_event(payload)


def test_parse_rc_event_missing_subscriber():
    payload = {"event": {"type": "BILLING_ISSUE"}}
    with pytest.raises(ValueError, match="missing event type or app_user_id"):
        parse_rc_event(payload)


# --- handle tests ---


def test_handle_billing_issue(tmp_path):
    engine = _make_engine(tmp_path)
    handler = RCWebhookHandler(engine)
    payload = {"event": {"type": "BILLING_ISSUE", "app_user_id": "sub_123"}}
    result = handler.handle(payload)
    assert result["processed"] is True
    assert result["action"] == "billing_issue_tracked"
    assert result["subscriber_id"] == "sub_123"


def test_handle_renewal(tmp_path):
    engine = _make_engine(tmp_path)
    engine.handle_billing_issue("sub_123")
    handler = RCWebhookHandler(engine)
    payload = {"event": {"type": "RENEWAL", "app_user_id": "sub_123"}}
    result = handler.handle(payload)
    assert result["processed"] is True
    assert result["action"] == "marked_recovered"
    assert result["subscriber_id"] == "sub_123"


def test_handle_uncancellation(tmp_path):
    engine = _make_engine(tmp_path)
    engine.handle_billing_issue("sub_123")
    handler = RCWebhookHandler(engine)
    payload = {"event": {"type": "UNCANCELLATION", "app_user_id": "sub_123"}}
    result = handler.handle(payload)
    assert result["processed"] is True
    assert result["action"] == "marked_recovered"
    assert result["subscriber_id"] == "sub_123"


def test_handle_expiration(tmp_path):
    engine = _make_engine(tmp_path)
    engine.handle_billing_issue("sub_123")
    handler = RCWebhookHandler(engine)
    payload = {"event": {"type": "EXPIRATION", "app_user_id": "sub_123"}}
    result = handler.handle(payload)
    assert result["processed"] is True
    assert result["action"] == "marked_churned"
    assert result["subscriber_id"] == "sub_123"


def test_handle_initial_purchase(tmp_path):
    engine = _make_engine(tmp_path)
    handler = RCWebhookHandler(engine)
    payload = {"event": {"type": "INITIAL_PURCHASE", "app_user_id": "sub_123"}}
    result = handler.handle(payload)
    assert result["processed"] is False
    assert result["action"] == "ignored"
    assert result["subscriber_id"] == "sub_123"


def test_handle_cancellation(tmp_path):
    engine = _make_engine(tmp_path)
    handler = RCWebhookHandler(engine)
    payload = {"event": {"type": "CANCELLATION", "app_user_id": "sub_123"}}
    result = handler.handle(payload)
    assert result["processed"] is False
    assert result["action"] == "ignored_cancellation"
    assert result["subscriber_id"] == "sub_123"


def test_handle_renewal_unknown_subscriber(tmp_path):
    engine = _make_engine(tmp_path)
    handler = RCWebhookHandler(engine)
    payload = {"event": {"type": "RENEWAL", "app_user_id": "sub_unknown"}}
    result = handler.handle(payload)
    assert result["processed"] is False
    assert result["action"] == "ignored_unknown"
    assert result["subscriber_id"] == "sub_unknown"


# --- auth tests ---


def test_auth_valid(tmp_path):
    engine = _make_engine(tmp_path)
    handler = RCWebhookHandler(engine, auth_key="secret123")
    payload = {"event": {"type": "BILLING_ISSUE", "app_user_id": "sub_123"}}
    result = handler.handle(payload, auth_header="secret123")
    assert result["processed"] is True
    assert result["action"] == "billing_issue_tracked"


def test_auth_invalid(tmp_path):
    engine = _make_engine(tmp_path)
    handler = RCWebhookHandler(engine, auth_key="secret123")
    payload = {"event": {"type": "BILLING_ISSUE", "app_user_id": "sub_123"}}
    with pytest.raises(ValueError, match="Webhook authentication failed"):
        handler.handle(payload, auth_header="wrong_key")


def test_auth_not_configured(tmp_path):
    engine = _make_engine(tmp_path)
    handler = RCWebhookHandler(engine)
    payload = {"event": {"type": "BILLING_ISSUE", "app_user_id": "sub_123"}}
    result = handler.handle(payload, auth_header="anything")
    assert result["processed"] is True
    assert result["action"] == "billing_issue_tracked"
