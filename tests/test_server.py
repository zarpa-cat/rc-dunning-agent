import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    """Create a test client with a temporary database."""
    db_path = str(tmp_path / "test.db")
    with patch.dict(os.environ, {"DUNNING_DB_PATH": db_path, "RC_WEBHOOK_SECRET": ""}):
        # Re-import to pick up patched env
        import importlib
        import rc_dunning_agent.server as server_mod

        importlib.reload(server_mod)
        yield TestClient(server_mod.app)


@pytest.fixture
def authed_client(tmp_path):
    """Create a test client that requires webhook auth."""
    db_path = str(tmp_path / "test.db")
    with patch.dict(os.environ, {"DUNNING_DB_PATH": db_path, "RC_WEBHOOK_SECRET": "secret123"}):
        import importlib
        import rc_dunning_agent.server as server_mod

        importlib.reload(server_mod)
        yield TestClient(server_mod.app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_billing_issue(client):
    payload = {
        "event": {
            "type": "BILLING_ISSUE",
            "app_user_id": "sub_1",
        }
    }
    response = client.post("/webhook/revenuecat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["processed"] is True
    assert data["action"] == "billing_issue_tracked"
    assert data["subscriber_id"] == "sub_1"


def test_webhook_renewal(client):
    # First create a billing issue
    client.post("/webhook/revenuecat", json={
        "event": {"type": "BILLING_ISSUE", "app_user_id": "sub_2"}
    })
    # Then renew
    response = client.post("/webhook/revenuecat", json={
        "event": {"type": "RENEWAL", "app_user_id": "sub_2"}
    })
    assert response.status_code == 200
    assert response.json()["action"] == "marked_recovered"


def test_webhook_invalid_payload(client):
    response = client.post("/webhook/revenuecat", json={"event": {}})
    assert response.status_code == 401


def test_webhook_auth_required(authed_client):
    payload = {"event": {"type": "BILLING_ISSUE", "app_user_id": "sub_1"}}
    # No auth header → 401
    response = authed_client.post("/webhook/revenuecat", json=payload)
    assert response.status_code == 401


def test_webhook_auth_valid(authed_client):
    payload = {"event": {"type": "BILLING_ISSUE", "app_user_id": "sub_1"}}
    response = authed_client.post(
        "/webhook/revenuecat",
        json=payload,
        headers={"RC-Webhook-Secret": "secret123"},
    )
    assert response.status_code == 200
    assert response.json()["processed"] is True


def test_webhook_auth_invalid(authed_client):
    payload = {"event": {"type": "BILLING_ISSUE", "app_user_id": "sub_1"}}
    response = authed_client.post(
        "/webhook/revenuecat",
        json=payload,
        headers={"RC-Webhook-Secret": "wrong"},
    )
    assert response.status_code == 401


def test_webhook_ignored_event(client):
    payload = {"event": {"type": "INITIAL_PURCHASE", "app_user_id": "sub_1"}}
    response = client.post("/webhook/revenuecat", json=payload)
    assert response.status_code == 200
    assert response.json()["processed"] is False
    assert response.json()["action"] == "ignored"


def test_webhook_expiration(client):
    # Create billing issue first
    client.post("/webhook/revenuecat", json={
        "event": {"type": "BILLING_ISSUE", "app_user_id": "sub_3"}
    })
    response = client.post("/webhook/revenuecat", json={
        "event": {"type": "EXPIRATION", "app_user_id": "sub_3"}
    })
    assert response.status_code == 200
    assert response.json()["action"] == "marked_churned"
