
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_session
from app.recommendations.contracts import RecommendationResponse
from app.recommendations.provider import (
    GeminiRecommendationProvider,
    RecommendationProvider,
)
from app.recommendations.service import (
    IncidentNotFoundError,
    generate_recommendation,
    get_latest_recommendation,
)

router = APIRouter(prefix="/api/v1/incidents", tags=["recommendations"])

logger = logging.getLogger(__name__)


def get_recommendation_provider() -> RecommendationProvider | None:
    api_key = settings.gemini_api_key

    if api_key is None or not api_key.get_secret_value().strip():
        logger.warning(
            "Gemini provider unavailable: GEMINI_API_KEY is missing or empty"
        )
        return None

    try:
        return GeminiRecommendationProvider(
            api_key.get_secret_value(),
            settings.gemini_model,
            settings.gemini_timeout_seconds,
        )
    except Exception as error:
        logger.exception(
            "Gemini provider initialization failed (%s)",
            type(error).__name__,
        )
        return None


@router.post(
    "/{incident_id}/recommendation",
    response_model=RecommendationResponse,
)
def create_incident_recommendation(
    incident_id: UUID,
    session: Session = Depends(get_session),
    provider: RecommendationProvider | None = Depends(get_recommendation_provider),
) -> RecommendationResponse:
    try:
        with session.begin():
            return generate_recommendation(session, incident_id, provider)
    except IncidentNotFoundError as error:
        raise HTTPException(status_code=404, detail="Incident not found") from error


@router.get(
    "/{incident_id}/recommendation",
    response_model=RecommendationResponse | None,
)
def read_latest_incident_recommendation(
    incident_id: UUID,
    session: Session = Depends(get_session),
) -> RecommendationResponse | None:
    try:
        return get_latest_recommendation(session, incident_id)
    except IncidentNotFoundError as error:
        raise HTTPException(status_code=404, detail="Incident not found") from error
