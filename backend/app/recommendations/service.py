import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Incident, Recommendation, Zone
from app.recommendations import repository
from app.recommendations.contracts import (
    EvidenceFact,
    RecommendationAction,
    RecommendationDraft,
    RecommendationInput,
    RecommendationResponse,
)
from app.recommendations.provider import RecommendationProvider

logger = logging.getLogger(__name__)


class IncidentNotFoundError(Exception):
    pass


def build_recommendation_input(incident: Incident, zone: Zone) -> RecommendationInput:
    facts = [
        EvidenceFact(
            id="incident.type",
            label="Rule-detected incident type",
            value=incident.type,
            source="incidents.type",
        ),
        EvidenceFact(
            id="incident.severity",
            label="Rule-assigned severity",
            value=incident.severity,
            source="incidents.severity",
        ),
        EvidenceFact(
            id="incident.source",
            label="Detection source",
            value=incident.source,
            source="incidents.source",
        ),
        EvidenceFact(
            id="incident.status",
            label="Incident status",
            value=incident.status,
            source="incidents.status",
        ),
        EvidenceFact(
            id="zone.name",
            label="Campus zone",
            value=zone.name,
            source="zones.name",
        ),
        EvidenceFact(
            id="zone.type",
            label="Zone type",
            value=zone.type,
            source="zones.type",
        ),
    ]
    if incident.current_value is not None:
        facts.append(
            EvidenceFact(
                id="incident.current_value",
                label="Rule-recorded current value",
                value=str(incident.current_value),
                source="incidents.current_value",
            )
        )
    if incident.expected_range is not None:
        facts.append(
            EvidenceFact(
                id="incident.expected_range",
                label="Rule-recorded expected range",
                value=incident.expected_range,
                source="incidents.expected_range",
            )
        )
    if incident.type == "ABNORMAL_OCCUPANCY":
        facts.append(
            EvidenceFact(
                id="zone.capacity",
                label="Zone capacity",
                value=str(zone.capacity),
                source="zones.capacity",
            )
        )

    return RecommendationInput(
        incident_id=incident.id,
        incident_type=incident.type,
        severity=incident.severity,
        incident_source=incident.source,
        incident_status=incident.status,
        zone_name=zone.name,
        zone_type=zone.type,
        facts=facts,
    )


def _fallback_draft(context: RecommendationInput) -> RecommendationDraft:
    fact_ids = {fact.id for fact in context.facts}
    incident_type = context.incident_type

    if incident_type == "HIGH_ENERGY_CONSUMPTION":
        explanation = "The deterministic rules recorded energy above its expected range."
        title = "Verify the energy reading"
        action = "Compare the recorded value with the meter and expected range before acting."
        rationale = "This checks the rule-recorded measurement without assuming its cause."
        evidence = ["incident.type", "incident.current_value", "incident.expected_range"]
    elif incident_type == "POSSIBLE_WATER_LEAKAGE":
        explanation = (
            "The deterministic rules recorded high water use with relatively stable occupancy; "
            "a leak is possible but is not confirmed."
        )
        title = "Inspect water use onsite"
        action = "Verify the meter reading and inspect relevant fixtures for visible leakage."
        rationale = "The recorded incident is a possible leak, not a confirmed cause."
        evidence = ["incident.type", "incident.current_value", "incident.expected_range"]
    elif incident_type == "ABNORMAL_OCCUPANCY":
        explanation = "The deterministic rules recorded occupancy above the zone capacity."
        title = "Verify occupancy and follow site procedure"
        action = "Confirm the occupancy count and follow the campus safety procedure for this zone."
        rationale = "The recommendation is based on the recorded count and configured capacity."
        evidence = ["incident.type", "incident.current_value", "zone.capacity"]
    elif incident_type == "WASTE_ACCUMULATION":
        explanation = "The deterministic waste rules recorded a HIGH waste level."
        title = "Review detector output and inspect the area"
        action = "Review the recorded detector output and arrange a manual site check."
        rationale = (
            "Detector labels are evidence for review, not confirmation of every waste class."
        )
        evidence = ["incident.type", "incident.current_value", "incident.source"]
    else:
        explanation = "The deterministic rules recorded an incident requiring review."
        title = "Verify the reported condition"
        action = "Check the source measurement and follow the relevant campus operating procedure."
        rationale = "The available incident facts do not establish a cause."
        evidence = ["incident.type", "incident.severity"]

    valid_evidence = [fact_id for fact_id in evidence if fact_id in fact_ids]
    if not valid_evidence:
        valid_evidence = ["incident.type"]
    return RecommendationDraft(
        explanation=explanation,
        recommendations=[
            RecommendationAction(
                title=title,
                action=action,
                rationale=rationale,
                supporting_fact_ids=valid_evidence,
            )
        ],
    )


def _validate_draft(
    draft: RecommendationDraft, context: RecommendationInput
) -> RecommendationDraft:
    if not draft.explanation.strip() or not draft.recommendations:
        raise ValueError("Recommendation output is incomplete")
    fact_ids = {fact.id for fact in context.facts}
    for recommendation in draft.recommendations:
        if not recommendation.title.strip() or not recommendation.action.strip():
            raise ValueError("Recommendation action is incomplete")
        if not recommendation.supporting_fact_ids:
            raise ValueError("Recommendation must cite at least one fact")
        if not set(recommendation.supporting_fact_ids).issubset(fact_ids):
            raise ValueError("Recommendation cited an unknown fact")
    return draft


def _response(
    recommendation: Recommendation,
) -> RecommendationResponse:
    content = recommendation.content
    return RecommendationResponse(
        id=recommendation.id,
        incident_id=recommendation.incident_id,
        provider=recommendation.provider,
        model=content["model"],
        mode=content["mode"],
        fallback_reason=content["fallback_reason"],
        generated_at=recommendation.created_at,
        facts=content["facts"],
        explanation=content["explanation"],
        recommendations=content["recommendations"],
    )


def get_latest_recommendation(
    session: Session, incident_id: UUID
) -> RecommendationResponse | None:
    if repository.get_incident_context(session, incident_id) is None:
        raise IncidentNotFoundError
    recommendation = repository.get_latest_recommendation(session, incident_id)
    return None if recommendation is None else _response(recommendation)


def generate_recommendation(
    session: Session,
    incident_id: UUID,
    provider: RecommendationProvider | None,
) -> RecommendationResponse:
    incident_context = repository.get_incident_context(session, incident_id)
    if incident_context is None:
        raise IncidentNotFoundError
    incident, zone = incident_context
    context = build_recommendation_input(incident, zone)

    mode = "ai"
    provider_name = "openai"
    model_name = settings.openai_model
    fallback_reason: str | None = None
    try:
        if provider is None:
            raise RuntimeError("AI provider is not configured")
        draft = RecommendationDraft.model_validate(provider.generate(context))
        draft = _validate_draft(draft, context)
        provider_name = provider.provider_name
        model_name = provider.model_name
    except Exception as error:
        mode = "fallback"
        provider_name = "rule-based-fallback"
        model_name = "none"
        fallback_reason = (
            "AI recommendations are unavailable; rule-based guidance is shown."
        )
        logger.warning(
            "Recommendation fallback used (%s): %s",
            type(error).__name__,
            error,
        )
        draft = _fallback_draft(context)

    content: dict[str, object] = {
        "schema_version": 1,
        "mode": mode,
        "model": model_name,
        "fallback_reason": fallback_reason,
        "facts": [fact.model_dump(mode="json") for fact in context.facts],
        "explanation": draft.explanation,
        "recommendations": [
            recommendation.model_dump(mode="json")
            for recommendation in draft.recommendations
        ],
    }
    saved = repository.create_recommendation(
        session, incident.id, content, provider_name
    )
    return _response(saved)