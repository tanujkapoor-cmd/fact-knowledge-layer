"""Tests for separate and explainable confidence measurements."""

from types import SimpleNamespace

from backend.extraction import EvidenceVerifier, FactCandidate
from backend.models import CheckOutcome, EvidenceReference, EvidenceStatus
from backend.reasoning import (
    classify_relationship,
    normalize_fact,
    score_classification,
    score_evidence_verification,
    score_extraction,
)


def _candidate() -> FactCandidate:
    return FactCandidate(
        subject="Acme",
        predicate="revenue",
        value="100",
        unit=None,
        currency=None,
        temporal_scope="FY2024",
        evidence_quote="Acme revenue was 100.",
        page_number=1,
    )


def _normalized(value: str, *, time: str = "FY2024"):
    return normalize_fact(
        SimpleNamespace(
            subject="Acme",
            predicate="revenue",
            value=value,
            unit=None,
            currency=None,
            temporal_scope=time,
        )
    )


def test_extraction_confidence_reports_contract_checks_not_truth() -> None:
    candidate = _candidate()
    evidence = EvidenceReference(
        physical_page_number=1,
        quote=candidate.evidence_quote,
        start_offset=0,
        end_offset=len(candidate.evidence_quote),
        status=EvidenceStatus.VERIFIED,
    )

    score = score_extraction(candidate, evidence)

    assert score.value == 1.0
    assert "not whether the claim is true" in score.reasons[-1]


def test_bad_page_reference_reduces_only_extraction_confidence() -> None:
    candidate = _candidate()
    evidence = EvidenceReference(
        physical_page_number=99,
        quote=candidate.evidence_quote,
        status=EvidenceStatus.FAILED,
        failure_reason="the model cited a page outside its supplied page batch",
    )

    score = score_extraction(candidate, evidence)

    assert score.value == 0.8
    assert "cited_page_was_supplied" in score.reasons[1]


def test_evidence_confidence_uses_measured_alignment_and_failure_is_zero() -> None:
    exact = EvidenceVerifier().verify("Acme revenue was 100.", "Acme revenue was 100.")
    failed = EvidenceVerifier().verify("Acme revenue was 100.", "A fabricated statement.")

    assert score_evidence_verification(exact).value == 1.0
    assert score_evidence_verification(failed).value == 0.0


def test_classification_confidence_counts_conclusive_checks() -> None:
    deterministic = classify_relationship(_normalized("100"), _normalized("120"))
    incomplete_context = classify_relationship(
        _normalized("100", time="FY2024"),
        _normalized("120", time="current period"),
    )

    confident = score_classification(deterministic).classification
    less_confident = score_classification(incomplete_context).classification

    assert confident.value == 1.0
    assert less_confident.value < 1.0
    assert any("judgment required" in reason for reason in less_confident.reasons)
    assert any(
        step.outcome is CheckOutcome.JUDGMENT_REQUIRED
        for step in incomplete_context.reasoning_trace
    )
