from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_notification_status_reports_missing_provider_without_exposing_settings(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "email_alerts_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", None)
    monkeypatch.setattr(settings, "smtp_from_email", None)
    monkeypatch.setattr(settings, "critical_alert_recipient", None)

    with TestClient(app) as client:
        response = client.get("/api/v1/notifications/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == {"status": "NOT_CONFIGURED", "enabled": False}
    assert payload["whatsapp"] == {"status": "NOT_CONFIGURED", "enabled": False}
    assert "smtp_password" not in response.text
    assert "critical_alert_recipient" not in response.text


def test_notification_status_reports_ready_email_configuration(monkeypatch) -> None:
    monkeypatch.setattr(settings, "email_alerts_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.invalid")
    monkeypatch.setattr(settings, "smtp_from_email", "alerts@example.invalid")
    monkeypatch.setattr(settings, "critical_alert_recipient", "ops@example.invalid")

    with TestClient(app) as client:
        response = client.get("/api/v1/notifications/status")

    assert response.status_code == 200
    assert response.json()["email"] == {"status": "READY", "enabled": True}
    assert response.json()["whatsapp"] == {
        "status": "NOT_CONFIGURED",
        "enabled": False,
    }
