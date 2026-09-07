"""Foundational domain contract tests."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.models import (
    CheckOutcome,
    ConfidenceScore,
    EvidenceReference,
    EvidenceStatus,
    ReasoningStep,
    Relationship,
    RelationshipConfidence,
    RelationshipType,
    TemporalScope,
)


def test_verified_evidence_requires_both_offsets() -> None:
    with pytest.raises(ValidationError, match="verified evidence requires source offsets"):
        EvidenceReference(
            physical_page_number=1,
            quote="Revenue increased by 10%.",
            status=EvidenceStatus.VERIFIED,
        )


def test_failed_evidence_requires_a_reason() -> None:
    with pytest.raises(ValidationError, match="failed evidence requires a failure_reason"):
        EvidenceReference(
            physical_page_number=1,
            quote="A fabricated quote",
            status=EvidenceStatus.FAILED,
        )


def test_evidence_quote_whitespace_is_preserved_verbatim() -> None:
    evidence = EvidenceReference(
        physical_page_number=1,
        quote="  exact source text  ",
        start_offset=4,
        end_offset=25,
        status=EvidenceStatus.VERIFIED,
    )

    assert evidence.quote == "  exact source text  "


def test_confidence_is_bounded_and_explainable() -> None:
    score = ConfidenceScore(
        value=0.75,
        method="required_fields_present",
        reasons=["subject, predicate and value were returned"],
    )

    assert score.value == 0.75
    with pytest.raises(ValidationError):
        ConfidenceScore(value=1.1, method="invalid")


def test_relationship_requires_two_distinct_facts() -> None:
    fact_id = uuid4()

    with pytest.raises(ValidationError, match="two distinct facts"):
        Relationship(
            id=uuid4(),
            fact_a_id=fact_id,
            fact_b_id=fact_id,
            classification=RelationshipType.UNCERTAIN,
            confidence=RelationshipConfidence(
                classification=ConfidenceScore(
                    value=0.5,
                    method="deterministic_checks",
                )
            ),
            reasoning_trace=[
                ReasoningStep(
                    order=1,
                    check="same_entity",
                    outcome=CheckOutcome.JUDGMENT_REQUIRED,
                )
            ],
        )


def test_temporal_scope_rejects_reversed_date_range() -> None:
    with pytest.raises(ValidationError, match="start_date must be on or before end_date"):
        TemporalScope(start_date="2026-12-31", end_date="2026-01-01")
