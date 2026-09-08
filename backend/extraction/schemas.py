"""Strict schemas for LLM candidates and verified extraction results."""

from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from backend.models import EvidenceReference, EvidenceStatus, FactConfidence

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
OptionalCleanText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None


class ExtractionModel(BaseModel):
    """Strict extraction model that does not silently accept extra LLM fields."""

    model_config = ConfigDict(extra="forbid")


class FactCandidate(ExtractionModel):
    """One atomic fact proposed by the LLM.

    Nullable fields intentionally have no defaults so they remain required in
    the strict JSON schema while still allowing an explicit null value.
    """

    subject: NonEmptyText = Field(
        description="Entity or population the claim is about; excludes the measured metric."
    )
    predicate: NonEmptyText = Field(
        description=(
            "Comparable property, metric, relationship, or event as a concise noun phrase; "
            "never only is/was/had/amounted to."
        )
    )
    value: NonEmptyText = Field(
        description="Asserted value or outcome only; excludes the subject and predicate."
    )
    unit: OptionalCleanText
    currency: OptionalCleanText
    temporal_scope: OptionalCleanText
    scope: OptionalCleanText
    data_vintage: OptionalCleanText
    evidence_quote: str = Field(min_length=1)
    page_number: int = Field(ge=1)


class FactCandidateBatch(ExtractionModel):
    """Schema-constrained payload returned from one model call."""

    facts: list[FactCandidate]


class AdapterExtractionResult(ExtractionModel):
    """Provider-neutral result returned by an extraction adapter."""

    candidates: list[FactCandidate]
    request_id: str | None = None
    attempt_count: int = Field(default=1, ge=1)


class EntityMatchDecision(ExtractionModel):
    """LLM tie-break result; it can match entities but cannot classify facts."""

    pair_id: NonEmptyText
    same_entity: bool
    explanation: NonEmptyText


class EntityMatchBatch(ExtractionModel):
    decisions: list[EntityMatchDecision]


class EvidenceMatchMethod(StrEnum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    FUZZY = "fuzzy"
    NONE = "none"


class EvidenceVerification(ExtractionModel):
    """Detailed evidence-alignment result used later for confidence scoring."""

    status: EvidenceStatus
    method: EvidenceMatchMethod
    similarity_score: float = Field(ge=0.0, le=100.0)
    requested_quote: str = Field(min_length=1)
    source_quote: str | None = None
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    failure_reason: str | None = None

    @model_validator(mode="after")
    def validate_match_state(self) -> Self:
        offsets = (self.start_offset, self.end_offset)
        if self.status is EvidenceStatus.VERIFIED:
            if self.method is EvidenceMatchMethod.NONE:
                raise ValueError("verified evidence requires a match method")
            if self.source_quote is None or offsets[0] is None or offsets[1] is None:
                raise ValueError("verified evidence requires a source quote and offsets")
        else:
            if self.method is not EvidenceMatchMethod.NONE:
                raise ValueError("failed evidence cannot have a match method")
            if not self.failure_reason:
                raise ValueError("failed evidence requires a reason")
        return self


class ExtractedFactRecord(ExtractionModel):
    """Candidate plus its independently verified evidence outcome."""

    candidate: FactCandidate
    evidence: EvidenceReference
    verification: EvidenceVerification
    confidence: FactConfidence
    classification_eligible: bool

    @model_validator(mode="after")
    def validate_eligibility(self) -> Self:
        is_verified = self.evidence.status is EvidenceStatus.VERIFIED
        if self.classification_eligible != is_verified:
            raise ValueError("only evidence-verified facts are classification eligible")
        if self.verification.status is not self.evidence.status:
            raise ValueError("verification details and evidence status must agree")
        return self


class ExtractionRun(ExtractionModel):
    """Combined result from one or more page-batched model calls."""

    provider: NonEmptyText
    model: NonEmptyText
    prompt_version: NonEmptyText
    request_ids: list[str] = Field(default_factory=list)
    provider_attempts: int = Field(default=0, ge=0)
    facts: list[ExtractedFactRecord]


class ExtractionCheckpoint(ExtractionModel):
    """Durable progress emitted after one complete page batch."""

    completed_pages: int = Field(ge=0)
    total_pages: int = Field(ge=1)
    completed_batches: int = Field(ge=0)
    facts_seen: int = Field(ge=0)
    provider_attempts: int = Field(ge=0)
