from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EvidenceFact(BaseModel):
    id: str
    label: str
    value: str
    source: str


class RecommendationInput(BaseModel):
    incident_id: UUID
    incident_type: str
    severity: str
    incident_source: str
    incident_status: str
    zone_name: str
    zone_type: str
    facts: list[EvidenceFact]


class RecommendationAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    action: str
    rationale: str
    supporting_fact_ids: list[str]


class RecommendationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explanation: str
    recommendations: list[RecommendationAction]


class RecommendationResponse(BaseModel):
    id: UUID
    incident_id: UUID
    provider: str
    model: str
    mode: Literal["ai", "fallback"]
    fallback_reason: str | None
    generated_at: datetime
    facts: list[EvidenceFact]
    explanation: str
    recommendations: list[RecommendationAction]