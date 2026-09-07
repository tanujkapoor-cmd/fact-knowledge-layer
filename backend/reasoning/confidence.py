"""Transparent, independently interpretable confidence scoring functions."""

from collections.abc import Sequence
from typing import Protocol

from backend.models import (
    CheckOutcome,
    ConfidenceScore,
    FactConfidence,
    ReasoningStep,
    RelationshipConfidence,
)

CONFIDENCE_VERSION = "confidence-v1"


class _CandidateLike(Protocol):
    subject: str
    predicate: str
    value: str
    evidence_quote: str


class _EvidenceLike(Protocol):
    failure_reason: str | None


class _VerificationLike(Protocol):
    status: object
    method: object
    similarity_score: float
    failure_reason: str | None


class _DecisionLike(Protocol):
    reasoning_trace: Sequence[ReasoningStep]


def score_extraction(
    candidate: _CandidateLike,
    evidence: _EvidenceLike,
) -> ConfidenceScore:
    """Score compliance with the structured extraction contract."""

    page_is_valid = not (
        evidence.failure_reason and "outside its supplied page batch" in evidence.failure_reason
    )
    checks = {
        "subject_present": bool(candidate.subject.strip()),
        "predicate_present": bool(candidate.predicate.strip()),
        "value_present": bool(candidate.value.strip()),
        "evidence_quote_present": bool(candidate.evidence_quote.strip()),
        "cited_page_was_supplied": page_is_valid,
    }
    passed = sum(checks.values())
    failed = [name for name, outcome in checks.items() if not outcome]
    reasons = [f"{passed}/{len(checks)} structured extraction checks passed"]
    if failed:
        reasons.append(f"failed checks: {', '.join(failed)}")
    reasons.append("this measures schema adherence, not whether the claim is true")
    return ConfidenceScore(
        value=passed / len(checks),
        method="structured_contract_checks_v1",
        reasons=reasons,
    )


def score_evidence_verification(verification: _VerificationLike) -> ConfidenceScore:
    """Map the measured source-alignment similarity to a bounded score."""

    verified = str(verification.status) == "verified"
    value = verification.similarity_score / 100 if verified else 0.0
    if verified:
        reasons = [
            f"verified by {verification.method} alignment",
            f"source alignment similarity was {verification.similarity_score:.2f}/100",
        ]
    else:
        reasons = [verification.failure_reason or "evidence did not verify"]
    return ConfidenceScore(
        value=value,
        method="source_alignment_similarity_v1",
        reasons=reasons,
    )


def score_fact_confidence(
    candidate: _CandidateLike,
    evidence: _EvidenceLike,
    verification: _VerificationLike,
) -> FactConfidence:
    """Return separate extraction and evidence scores without averaging them."""

    return FactConfidence(
        extraction=score_extraction(candidate, evidence),
        evidence_verification=score_evidence_verification(verification),
    )


def score_classification(decision: _DecisionLike) -> RelationshipConfidence:
    """Score the share of applicable checks resolved without a judgment call."""

    applicable = [
        step for step in decision.reasoning_trace if step.outcome is not CheckOutcome.SKIPPED
    ]
    conclusive = [
        step for step in applicable if step.outcome in {CheckOutcome.PASSED, CheckOutcome.FAILED}
    ]
    judgments = [
        step.check for step in applicable if step.outcome is CheckOutcome.JUDGMENT_REQUIRED
    ]
    value = len(conclusive) / len(applicable) if applicable else 0.0
    reasons = [f"{len(conclusive)}/{len(applicable)} applicable checks were deterministic"]
    if judgments:
        reasons.append(f"judgment required for: {', '.join(judgments)}")
    else:
        reasons.append("no judgment call was required")
    return RelationshipConfidence(
        classification=ConfidenceScore(
            value=value,
            method="conclusive_deterministic_checks_v1",
            reasons=reasons,
        )
    )
