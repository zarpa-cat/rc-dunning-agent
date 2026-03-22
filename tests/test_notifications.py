from unittest.mock import patch, MagicMock

import pytest

from rc_dunning_agent.notifications import (
    NotificationService,
    ResendConfig,
    SlackConfig,
)
from rc_dunning_agent.templates import FIRST_NUDGE, SECOND_NUDGE


def test_send_email_dry_run():
    svc = NotificationService()
    result = svc.send_email(
        subscriber_id="sub_1",
        template=FIRST_NUDGE,
        days_overdue=2,
        expiry_date="2026-04-01",
        dry_run=True,
    )
    assert result["status"] == "dry_run"
    assert "sub_1" in result["body"]
    assert "Action required" in result["subject"]


def test_send_email_dry_run_second_nudge():
    svc = NotificationService()
    result = svc.send_email(
        subscriber_id="sub_2",
        template=SECOND_NUDGE,
        days_overdue=3,
        expiry_date="2026-04-05",
        dry_run=True,
    )
    assert result["status"] == "dry_run"
    assert "Reminder" in result["subject"]


def test_send_email_no_config_raises():
    svc = NotificationService()
    with pytest.raises(ValueError, match="ResendConfig"):
        svc.send_email(subscriber_id="sub_1", template=FIRST_NUDGE)


@patch("rc_dunning_agent.notifications.httpx.post")
def test_send_email_calls_resend_api(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "email_123"}
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    svc = NotificationService(
        resend_config=ResendConfig(api_key="re_test_key", from_email="noreply@test.com")
    )
    result = svc.send_email(
        subscriber_id="sub_1",
        template=FIRST_NUDGE,
        to_email="user@test.com",
        days_overdue=1,
        expiry_date="2026-04-01",
    )
    assert result["status"] == "sent"
    assert result["resend_response"]["id"] == "email_123"
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert "https://api.resend.com/emails" in call_kwargs.args or call_kwargs.args[0] == "https://api.resend.com/emails"
    json_body = call_kwargs.kwargs["json"]
    assert json_body["from"] == "noreply@test.com"
    assert json_body["to"] == ["user@test.com"]


@patch("rc_dunning_agent.notifications.httpx.post")
def test_send_email_default_to_email(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "email_456"}
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    svc = NotificationService(
        resend_config=ResendConfig(api_key="re_key", from_email="noreply@test.com")
    )
    svc.send_email(subscriber_id="sub_1", template=FIRST_NUDGE)
    json_body = mock_post.call_args.kwargs["json"]
    assert json_body["to"] == ["sub_1@example.com"]


def test_send_slack_no_config_raises():
    svc = NotificationService()
    with pytest.raises(ValueError, match="SlackConfig"):
        svc.send_slack("hello")


@patch("rc_dunning_agent.notifications.httpx.post")
def test_send_slack_calls_webhook(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    svc = NotificationService(
        slack_config=SlackConfig(webhook_url="https://hooks.slack.com/test")
    )
    result = svc.send_slack("Recovery alert!")
    assert result["status"] == "sent"
    mock_post.assert_called_once_with(
        "https://hooks.slack.com/test",
        json={"text": "Recovery alert!"},
    )


@patch("rc_dunning_agent.notifications.httpx.post")
def test_send_email_auth_header(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "x"}
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    svc = NotificationService(
        resend_config=ResendConfig(api_key="re_secret", from_email="a@b.com")
    )
    svc.send_email(subscriber_id="sub_1", template=FIRST_NUDGE)
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer re_secret"
