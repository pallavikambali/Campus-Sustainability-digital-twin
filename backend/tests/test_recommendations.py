from collections.abc import Generator
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import engine, get_session
from app.main import app
from app.models import Incident, Zone
from app.recommendations.api import get_recommendation_provider
from app.recommendations.contracts import (
    RecommendationAction,
    RecommendationDraft,
    RecommendationInput,
)
from app.recommendations.provider import OpenAIRecommendationProvider


class FakeProvider:
    provider_name = "test-provider"
    model_name = "test-model"

    def __init__(self) -> None:
        self.context: RecommendationInput | None = None

    def generate(self, context: RecommendationInput) -> RecommendationDraft:
        self.context = context
        return RecommendationDraft(
            explanation="The rule recorded energy above the configured expected range.",
            recommendations=[
                RecommendationAction(
                    title="Verify the meter",
                    action="Compare the meter with the recorded reading.",
                    rationale="The incident stores a current value and expected range.",
                    supporting_fact_ids=[
                        "incident.current_value",
                        "incident.expected_range",
                    ],
                )
            ],
        )


@pytest.fixture
def recommendation_client() -> Generator[tuple[TestClient, UUID], None, None]:
    with Session(engine) as lookup_session:
        zone_id = lookup_session.scalar(
            select(Zone.id).where(Zone.name == "Academic Block")
        )
    assert zone_id is not None

    connection = engine.connect()
    transaction = connection.begin()
    with Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    ) as setup_session:
        incident = Incident(
            zone_id=zone_id,
            type="HIGH_ENERGY_CONSUMPTION",
            severity="HIGH",
            current_value=Decimal("360.00"),
            expected_range="0-180.00 kWh per reading",
            description="Energy consumption exceeded the expected range.",
            status="ACTIVE",
            source="RULE",
        )
        setup_session.add(incident)
        setup_session.flush()
        incident_id = incident.id
        setup_session.commit()

    previous_session_override = app.dependency_overrides.get(get_session)
    previous_provider_override = app.dependency_overrides.get(get_recommendation_provider)

    def override_get_session() -> Generator[Session, None, None]:
        with Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_recommendation_provider] = lambda: FakeProvider()
    try:
        with TestClient(app) as client:
            yield client, incident_id
    finally:
        if previous_session_override is None:
            app.dependency_overrides.pop(get_session, None)
        else:
            app.dependency_overrides[get_session] = previous_session_override
        if previous_provider_override is None:
            app.dependency_overrides.pop(get_recommendation_provider, None)
        else:
            app.dependency_overrides[get_recommendation_provider] = previous_provider_override
        transaction.rollback()
        connection.close()


def test_recommendation_uses_database_facts_and_persists_without_mutating_incident(
    recommendation_client: tuple[TestClient, UUID],
) -> None:
    client, incident_id = recommendation_client
    incident_before = client.get(f"/api/v1/incidents/{incident_id}").json()
    zone_id = incident_before["zone_id"]
    zone_status_before = client.get(f"/api/v1/zones/{zone_id}").json()["status"]
    readings_before = client.get(f"/api/v1/readings?zone_id={zone_id}&limit=100").json()

    response = client.post(f"/api/v1/incidents/{incident_id}/recommendation")

    assert response.status_code == 200
    result = response.json()
    assert result["mode"] == "ai"
    assert result["provider"] == "test-provider"
    assert result["model"] == "test-model"
    assert {fact["id"] for fact in result["facts"]} >= {
        "incident.current_value",
        "incident.expected_range",
        "zone.name",
    }
    assert all(
        fact["id"] != "incident.description" for fact in result["facts"]
    )
    assert result["recommendations"][0]["supporting_fact_ids"] == [
        "incident.current_value",
        "incident.expected_range",
    ]

    latest_response = client.get(f"/api/v1/incidents/{incident_id}/recommendation")
    incident_response = client.get(f"/api/v1/incidents/{incident_id}")
    zone_status_after = client.get(f"/api/v1/zones/{zone_id}").json()["status"]
    readings_after = client.get(f"/api/v1/readings?zone_id={zone_id}&limit=100").json()
    assert latest_response.status_code == 200
    assert latest_response.json()["id"] == result["id"]
    assert incident_response.json()["status"] == "ACTIVE"
    assert incident_response.json()["current_value"] == "360.00"
    assert zone_status_after == zone_status_before
    assert readings_after == readings_before


def test_missing_provider_returns_persisted_rule_based_fallback(
    recommendation_client: tuple[TestClient, UUID],
) -> None:
    client, incident_id = recommendation_client
    app.dependency_overrides[get_recommendation_provider] = lambda: None

    response = client.post(f"/api/v1/incidents/{incident_id}/recommendation")

    assert response.status_code == 200
    result = response.json()
    assert result["mode"] == "fallback"
    assert result["provider"] == "rule-based-fallback"
    assert "unavailable" in result["fallback_reason"].lower()
    assert result["recommendations"]
    assert result["recommendations"][0]["supporting_fact_ids"]


def test_provider_error_uses_fallback_and_does_not_expose_secret(
    recommendation_client: tuple[TestClient, UUID],
) -> None:
    client, incident_id = recommendation_client

    class FailingProvider:
        provider_name = "openai"
        model_name = "gpt-4.1-mini"

        def generate(self, context: RecommendationInput) -> RecommendationDraft:
            raise RuntimeError("request failed with key sk-test-secret")

    app.dependency_overrides[get_recommendation_provider] = lambda: FailingProvider()
    response = client.post(f"/api/v1/incidents/{incident_id}/recommendation")

    assert response.status_code == 200
    assert response.json()["mode"] == "fallback"
    assert "sk-test-secret" not in response.text


@pytest.mark.parametrize(
    "provider_error",
    [
        RuntimeError("401 invalid_api_key sk-test-secret"),
        TimeoutError("OpenAI request timed out"),
    ],
)
def test_invalid_credentials_and_timeout_use_fallback(
    recommendation_client: tuple[TestClient, UUID],
    provider_error: Exception,
) -> None:
    client, incident_id = recommendation_client

    class UnavailableProvider:
        provider_name = "openai"
        model_name = "gpt-4.1-mini"

        def generate(self, context: RecommendationInput) -> RecommendationDraft:
            raise provider_error

    app.dependency_overrides[get_recommendation_provider] = lambda: UnavailableProvider()
    response = client.post(f"/api/v1/incidents/{incident_id}/recommendation")

    assert response.status_code == 200
    assert response.json()["mode"] == "fallback"
    assert "sk-test-secret" not in response.text


def test_malformed_provider_output_uses_fallback(
    recommendation_client: tuple[TestClient, UUID],
) -> None:
    client, incident_id = recommendation_client

    class MalformedProvider:
        provider_name = "openai"
        model_name = "gpt-4.1-mini"

        def generate(self, context: RecommendationInput) -> dict[str, object]:
            return {
                "explanation": "Malformed response.",
                "recommendations": [],
                "measurement": 999,
            }

    app.dependency_overrides[get_recommendation_provider] = lambda: MalformedProvider()
    response = client.post(f"/api/v1/incidents/{incident_id}/recommendation")

    assert response.status_code == 200
    assert response.json()["mode"] == "fallback"


def test_unknown_supporting_fact_id_uses_fallback(
    recommendation_client: tuple[TestClient, UUID],
) -> None:
    client, incident_id = recommendation_client

    class InvalidFactProvider:
        provider_name = "test-provider"
        model_name = "test-model"

        def generate(self, context: RecommendationInput) -> RecommendationDraft:
            return RecommendationDraft(
                explanation="This response cites an unavailable fact.",
                recommendations=[
                    RecommendationAction(
                        title="Take action",
                        action="Use this unsupported fact.",
                        rationale="The model invented a fact reference.",
                        supporting_fact_ids=["sensor.future_value"],
                    )
                ],
            )

    app.dependency_overrides[get_recommendation_provider] = lambda: InvalidFactProvider()
    response = client.post(f"/api/v1/incidents/{incident_id}/recommendation")

    assert response.status_code == 200
    assert response.json()["mode"] == "fallback"
    assert all(
        fact_id in {fact["id"] for fact in response.json()["facts"]}
        for recommendation in response.json()["recommendations"]
        for fact_id in recommendation["supporting_fact_ids"]
    )


def test_latest_recommendation_is_null_until_generated(
    recommendation_client: tuple[TestClient, UUID],
) -> None:
    client, incident_id = recommendation_client

    response = client.get(f"/api/v1/incidents/{incident_id}/recommendation")

    assert response.status_code == 200
    assert response.json() is None


def test_openai_adapter_uses_structured_response_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openai = pytest.importorskip("openai")
    context = RecommendationInput(
        incident_id=UUID("00000000-0000-4000-8000-000000000001"),
        incident_type="HIGH_ENERGY_CONSUMPTION",
        severity="HIGH",
        incident_source="RULE",
        incident_status="ACTIVE",
        zone_name="Academic Block",
        zone_type="ACADEMIC",
        facts=[],
    )
    draft = RecommendationDraft(
        explanation="The existing rule recorded an energy incident.",
        recommendations=[
            RecommendationAction(
                title="Verify the meter",
                action="Compare the meter with its recorded value.",
                rationale="This checks the existing measurement.",
                supporting_fact_ids=["incident.type"],
            )
        ],
    )
    parse_arguments: dict[str, object] = {}

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["api_key"] == "test-key"

        class chat:
            class completions:
                @staticmethod
                def parse(**kwargs: object) -> object:
                    parse_arguments.update(kwargs)
                    message = SimpleNamespace(refusal=None, parsed=draft)
                    choice = SimpleNamespace(message=message)
                    return SimpleNamespace(choices=[choice])

    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    provider = OpenAIRecommendationProvider("test-key", "gpt-4.1-mini", 5.0)

    result = provider.generate(context)

    assert result == draft
    assert parse_arguments["model"] == "gpt-4.1-mini"
    assert parse_arguments["response_format"] is RecommendationDraft
    assert "Do not invent" in parse_arguments["messages"][0]["content"]