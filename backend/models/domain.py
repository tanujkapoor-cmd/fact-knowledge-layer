"""Framework-independent domain contracts for facts and relationships."""

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DomainModel(BaseModel):
    """Strict base model used for all domain data crossing a boundary."""

    model_config = ConfigDict(extra="forbid")


class DocumentStatus(StrEnum):
    QUEUED = "queued"
    INGESTING = "ingesting"
    EXTRACTING = "extracting"
    VERIFYING = "verifying"
    NORMALIZING = "normalizing"
    CLASSIFYING = "classifying"
    COMPLETED = "completed"
    FAILED = "failed"


class EvidenceStatus(StrEnum):
    VERIFIED = "verified"
    FAILED = "failed"


class RelationshipType(StrEnum):
    CORROBORATES = "corroborates"
    CONTRADICTS = "contradicts"
    RECONCILED = "reconciled"
    UNCERTAIN = "uncertain"


class CheckOutcome(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    JUDGMENT_REQUIRED = "judgment_required"


class ConfidenceScore(DomainModel):
    """One independently interpretable confidence measurement."""

    value: float = Field(ge=0.0, le=1.0)
    method: NonEmptyText
    reasons: list[str] = Field(default_factory=list)


class FactConfidence(DomainModel):
    """Fact-level scores; intentionally not collapsed into one number."""

    extraction: ConfidenceScore
    evidence_verification: ConfidenceScore


class RelationshipConfidence(DomainModel):
    """Confidence in the deterministic relationship decision."""

    classification: ConfidenceScore


class TemporalScope(DomainModel):
    """Raw and parsed time information associated with a fact."""

    raw_text: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_date_order(self) -> Self:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


class EvidenceReference(DomainModel):
    """A page-local citation for a fact, including verification outcome."""

    physical_page_number: int = Field(ge=1)
    printed_page_label: str | None = None
    quote: str = Field(min_length=1)
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    status: EvidenceStatus
    failure_reason: str | None = None

    @model_validator(mode="after")
    def validate_verification_state(self) -> Self:
        offsets = (self.start_offset, self.end_offset)
        if (offsets[0] is None) != (offsets[1] is None):
            raise ValueError("start_offset and end_offset must be provided together")
        if offsets[0] is not None and offsets[1] is not None and offsets[1] <= offsets[0]:
            raise ValueError("end_offset must be greater than start_offset")
        if self.status is EvidenceStatus.VERIFIED and offsets[0] is None:
            raise ValueError("verified evidence requires source offsets")
        if self.status is EvidenceStatus.FAILED and not self.failure_reason:
            raise ValueError("failed evidence requires a failure_reason")
        return self


class Document(DomainModel):
    """Uploaded document identity and processing state."""

    id: UUID
    file_name: NonEmptyText
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: DocumentStatus
    created_at: datetime
    failure_reason: str | None = None


class Fact(DomainModel):
    """A source-grounded claim prior to deterministic normalization."""

    id: UUID
    document_id: UUID
    subject: NonEmptyText
    predicate: NonEmptyText
    value: NonEmptyText
    unit: str | None = None
    currency: str | None = None
    temporal_scope: TemporalScope | None = None
    scope: str | None = None
    data_vintage: TemporalScope | None = None
    evidence: EvidenceReference
    confidence: FactConfidence


class ReasoningStep(DomainModel):
    """One ordered, machine-readable classifier check."""

    order: int = Field(ge=1)
    check: NonEmptyText
    outcome: CheckOutcome
    details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class Relationship(DomainModel):
    """A deterministic decision connecting two facts."""

    id: UUID
    fact_a_id: UUID
    fact_b_id: UUID
    classification: RelationshipType
    confidence: RelationshipConfidence
    reasoning_trace: list[ReasoningStep] = Field(min_length=1)

    @model_validator(mode="after")
    def require_distinct_facts(self) -> Self:
        if self.fact_a_id == self.fact_b_id:
            raise ValueError("a relationship must reference two distinct facts")
        return self
