"""Schemas used at the HTTP boundary."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.models.domain import (
    ConfidenceScore,
    DocumentStatus,
    EvidenceReference,
    FactConfidence,
    ReasoningStep,
    RelationshipType,
)


class HealthResponse(BaseModel):
    """Health information returned by the service."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    database: Literal["ok"]
    version: str


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentUploadResponse(ApiModel):
    id: UUID
    file_name: str
    sha256: str
    status: DocumentStatus
    duplicate_reused: bool


class DocumentStatusResponse(ApiModel):
    id: UUID
    file_name: str
    sha256: str
    status: DocumentStatus
    created_at: datetime
    page_count: int | None = None
    failure_reason: str | None = None


class VerificationDetailsResponse(ApiModel):
    method: str
    similarity_score: float = Field(ge=0, le=100)


class FactResponse(ApiModel):
    id: UUID
    document_id: UUID
    subject: str
    predicate: str
    value: str
    unit: str | None = None
    currency: str | None = None
    temporal_scope: str | None = None
    evidence: EvidenceReference
    verification: VerificationDetailsResponse
    confidence: FactConfidence
    classification_eligible: bool


class RelationshipResponse(ApiModel):
    id: UUID
    classification: RelationshipType
    reconciliation_reasons: list[str]
    classification_confidence: ConfidenceScore
    reasoning_trace: list[ReasoningStep]
    fact_a: FactResponse
    fact_b: FactResponse
