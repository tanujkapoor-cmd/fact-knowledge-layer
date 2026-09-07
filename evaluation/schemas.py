"""Validated, document-agnostic contracts for human labels and predictions."""

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from backend.models import RelationshipType

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class EvaluationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentScope(EvaluationModel):
    """A document and optional physical pages on which extraction is exhaustive."""

    document_key: NonEmptyText
    physical_pages: list[int] | None = None


class EvaluationFact(EvaluationModel):
    """A fact representation shared by hand labels and system predictions."""

    id: NonEmptyText
    document_key: NonEmptyText
    subject: NonEmptyText
    predicate: NonEmptyText
    value: NonEmptyText
    unit: str | None = None
    currency: str | None = None
    temporal_scope: str | None = None
    physical_page_number: int = Field(ge=1)
    evidence_quote: NonEmptyText


class EvaluationRelationship(EvaluationModel):
    id: NonEmptyText
    fact_a_id: NonEmptyText
    fact_b_id: NonEmptyText
    classification: RelationshipType

    @model_validator(mode="after")
    def distinct_facts(self) -> Self:
        if self.fact_a_id == self.fact_b_id:
            raise ValueError("relationship labels require two different facts")
        return self


class EvaluationDataset(EvaluationModel):
    facts: list[EvaluationFact]
    relationships: list[EvaluationRelationship]

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        fact_ids = [fact.id for fact in self.facts]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("fact IDs must be unique")
        relationship_ids = [relationship.id for relationship in self.relationships]
        if len(relationship_ids) != len(set(relationship_ids)):
            raise ValueError("relationship IDs must be unique")
        unknown = {
            fact_id
            for relationship in self.relationships
            for fact_id in (relationship.fact_a_id, relationship.fact_b_id)
            if fact_id not in fact_ids
        }
        if unknown:
            raise ValueError(f"relationships reference unknown facts: {sorted(unknown)}")
        return self


class GroundTruthDataset(EvaluationDataset):
    """Human-authored labels plus the exhaustive scope used for precision."""

    scope: list[DocumentScope] = Field(min_length=1)


class PredictionDataset(EvaluationDataset):
    """System output exported into the neutral evaluation contract."""


class ExtractionMetrics(EvaluationModel):
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    exact_evidence_quote_rate: float | None


class RelationshipMetrics(EvaluationModel):
    labels: list[str]
    prediction_labels: list[str]
    confusion_matrix: list[list[int]]
    accuracy: float
    evaluated_pairs: int
    missing_predictions: int


class EvaluationResults(EvaluationModel):
    extraction: ExtractionMetrics
    relationships: RelationshipMetrics
