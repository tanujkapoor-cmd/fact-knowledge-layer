"""Pure deterministic relationship candidate generation and classification."""

import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from decimal import Decimal

from backend.models import CheckOutcome, ReasoningStep, RelationshipType
from backend.reasoning.schemas import (
    ClassificationDecision,
    NormalizedFact,
    ReconciliationReason,
    RelationshipCandidate,
    ValueKind,
)

CLASSIFIER_VERSION = "classifier-v1"
_CHECKS = (
    "same_entity",
    "same_predicate",
    "normalized_value_equality",
    "time_period",
    "unit",
    "currency",
    "scope",
)


def _step(
    order: int,
    check: str,
    outcome: CheckOutcome,
    **details: str | int | float | bool | None,
) -> ReasoningStep:
    return ReasoningStep(order=order, check=check, outcome=outcome, details=details)


def _finish_trace(trace: list[ReasoningStep], reason: str) -> tuple[ReasoningStep, ...]:
    """Make every early decision expose the complete ordered decision tree."""

    seen = {step.check for step in trace}
    for order, check in enumerate(_CHECKS, start=1):
        if check not in seen:
            trace.append(
                _step(order, check, CheckOutcome.SKIPPED, reason=reason)
            )
    return tuple(sorted(trace, key=lambda step: step.order))


def _decision(
    fact_a: NormalizedFact,
    fact_b: NormalizedFact,
    classification: RelationshipType,
    trace: list[ReasoningStep],
    *,
    reasons: Iterable[ReconciliationReason] = (),
    skipped_reason: str,
) -> ClassificationDecision:
    return ClassificationDecision(
        fact_a_id=fact_a.fact_id,
        fact_b_id=fact_b.fact_id,
        classification=classification,
        reconciliation_reasons=tuple(reasons),
        reasoning_trace=_finish_trace(trace, skipped_reason),
    )


def _normalized_scope(scope: str | None) -> str | None:
    if scope is None or not scope.strip():
        return None
    return " ".join(re.findall(r"[^\W_]+", scope.casefold()))


def _numeric_values_equal(left: Decimal, right: Decimal) -> bool:
    """Use exact Decimal equality; rounding tolerances must never be hidden."""

    return left == right


def _values_equal(fact_a: NormalizedFact, fact_b: NormalizedFact) -> bool | None:
    left = fact_a.value
    right = fact_b.value
    if left.kind is not right.kind:
        return None
    if left.kind is ValueKind.TEXT:
        return left.normalized_text == right.normalized_text

    if left.unit_dimension != right.unit_dimension:
        return None
    if left.canonical_currency != right.canonical_currency:
        return None
    assert left.normalized_numeric_value is not None
    assert right.normalized_numeric_value is not None
    return _numeric_values_equal(left.normalized_numeric_value, right.normalized_numeric_value)


def _different_representation_reasons(
    fact_a: NormalizedFact,
    fact_b: NormalizedFact,
) -> tuple[ReconciliationReason, ...]:
    reasons: list[ReconciliationReason] = []
    left = fact_a.value
    right = fact_b.value
    if (
        left.original_unit != right.original_unit
        and left.unit_dimension == right.unit_dimension
        and left.unit_dimension is not None
    ):
        reasons.append(ReconciliationReason.UNIT)
    source_currency_a = (left.original_currency or left.canonical_currency or "").upper()
    source_currency_b = (right.original_currency or right.canonical_currency or "").upper()
    if (
        source_currency_a
        and source_currency_b
        and source_currency_a != source_currency_b
        and left.canonical_currency == right.canonical_currency
    ):
        reasons.append(ReconciliationReason.CURRENCY)
    return tuple(reasons)


def _time_comparison(fact_a: NormalizedFact, fact_b: NormalizedFact) -> str:
    left = fact_a.temporal_scope
    right = fact_b.temporal_scope
    if left is None and right is None:
        return "same"
    if left is None or right is None:
        return "unknown"
    if not left.parsed or not right.parsed:
        if left.original_text.casefold().strip() == right.original_text.casefold().strip():
            return "same"
        return "unknown"
    if left.start_date == right.start_date and left.end_date == right.end_date:
        return "same"
    return "different"


def _comparison_gap(fact_a: NormalizedFact, fact_b: NormalizedFact) -> str | None:
    left = fact_a.value
    right = fact_b.value
    if left.kind is not right.kind:
        return "value kinds differ"
    if left.kind is ValueKind.NUMERIC:
        if left.unit_dimension != right.unit_dimension:
            return "unit dimensions are missing or incompatible"
        if left.canonical_currency != right.canonical_currency:
            return "currencies were not converted to a common dated basis"
    return None


def classify_relationship(
    fact_a: NormalizedFact,
    fact_b: NormalizedFact,
) -> ClassificationDecision:
    """Classify two normalized facts using the required ordered checks."""

    trace: list[ReasoningStep] = []

    same_entity = fact_a.entity.comparison_key == fact_b.entity.comparison_key
    trace.append(
        _step(
            1,
            "same_entity",
            CheckOutcome.PASSED if same_entity else CheckOutcome.FAILED,
            entity_a=fact_a.entity.comparison_key,
            entity_b=fact_b.entity.comparison_key,
        )
    )
    if not same_entity:
        return _decision(
            fact_a,
            fact_b,
            RelationshipType.UNCERTAIN,
            trace,
            skipped_reason="entities do not share a deterministic canonical key",
        )

    same_predicate = fact_a.canonical_predicate == fact_b.canonical_predicate
    trace.append(
        _step(
            2,
            "same_predicate",
            CheckOutcome.PASSED if same_predicate else CheckOutcome.FAILED,
            predicate_a=fact_a.canonical_predicate,
            predicate_b=fact_b.canonical_predicate,
        )
    )
    if not same_predicate:
        return _decision(
            fact_a,
            fact_b,
            RelationshipType.UNCERTAIN,
            trace,
            skipped_reason="predicates do not share a deterministic canonical key",
        )

    values_equal = _values_equal(fact_a, fact_b)
    value_outcome = (
        CheckOutcome.JUDGMENT_REQUIRED
        if values_equal is None
        else CheckOutcome.PASSED
        if values_equal
        else CheckOutcome.FAILED
    )
    trace.append(
        _step(
            3,
            "normalized_value_equality",
            value_outcome,
            value_a=str(
                fact_a.value.normalized_numeric_value or fact_a.value.normalized_text
            ),
            value_b=str(
                fact_b.value.normalized_numeric_value or fact_b.value.normalized_text
            ),
        )
    )

    if values_equal:
        representation_reasons = _different_representation_reasons(fact_a, fact_b)
        if representation_reasons:
            for reason in representation_reasons:
                order = 5 if reason is ReconciliationReason.UNIT else 6
                trace.append(
                    _step(
                        order,
                        reason.value,
                        CheckOutcome.PASSED,
                        explanation=f"normalized {reason.value} explains equivalent values",
                    )
                )
            return _decision(
                fact_a,
                fact_b,
                RelationshipType.RECONCILED,
                trace,
                reasons=representation_reasons,
                skipped_reason="equivalent values were reconciled by normalization",
            )
        return _decision(
            fact_a,
            fact_b,
            RelationshipType.CORROBORATES,
            trace,
            skipped_reason="normalized values are equal",
        )

    time_comparison = _time_comparison(fact_a, fact_b)
    trace.append(
        _step(
            4,
            "time_period",
            CheckOutcome.PASSED
            if time_comparison == "different"
            else CheckOutcome.JUDGMENT_REQUIRED
            if time_comparison == "unknown"
            else CheckOutcome.FAILED,
            comparison=time_comparison,
        )
    )
    if time_comparison == "different":
        return _decision(
            fact_a,
            fact_b,
            RelationshipType.RECONCILED,
            trace,
            reasons=(ReconciliationReason.TIME_PERIOD,),
            skipped_reason="different reporting periods explain the different values",
        )

    trace.append(
        _step(
            5,
            "unit",
            CheckOutcome.FAILED,
            unit_a=fact_a.value.canonical_unit,
            unit_b=fact_b.value.canonical_unit,
            dimension_a=fact_a.value.unit_dimension,
            dimension_b=fact_b.value.unit_dimension,
        )
    )
    trace.append(
        _step(
            6,
            "currency",
            CheckOutcome.FAILED,
            currency_a=fact_a.value.canonical_currency,
            currency_b=fact_b.value.canonical_currency,
        )
    )

    scope_a = _normalized_scope(fact_a.scope)
    scope_b = _normalized_scope(fact_b.scope)
    scopes_different = scope_a is not None and scope_b is not None and scope_a != scope_b
    scope_unknown = (scope_a is None) != (scope_b is None)
    trace.append(
        _step(
            7,
            "scope",
            CheckOutcome.PASSED
            if scopes_different
            else CheckOutcome.JUDGMENT_REQUIRED
            if scope_unknown
            else CheckOutcome.FAILED,
            scope_a=scope_a,
            scope_b=scope_b,
        )
    )
    if scopes_different:
        return _decision(
            fact_a,
            fact_b,
            RelationshipType.RECONCILED,
            trace,
            reasons=(ReconciliationReason.SCOPE,),
            skipped_reason="different scopes explain the different values",
        )

    gap = _comparison_gap(fact_a, fact_b)
    if time_comparison == "unknown" or scope_unknown or gap:
        return _decision(
            fact_a,
            fact_b,
            RelationshipType.UNCERTAIN,
            trace,
            skipped_reason=gap or "context is incomplete or ambiguous",
        )

    return _decision(
        fact_a,
        fact_b,
        RelationshipType.CONTRADICTS,
        trace,
        skipped_reason=(
            "same entity, predicate, time, unit, currency, and scope have unequal values"
        ),
    )


def block_relationship_candidates(
    facts: Sequence[NormalizedFact],
    *,
    cross_document_only: bool = True,
) -> list[RelationshipCandidate]:
    """Generate pairs only within exact canonical entity-and-predicate blocks."""

    blocks: dict[tuple[str, str], list[NormalizedFact]] = defaultdict(list)
    for fact in facts:
        blocks[(fact.entity.comparison_key, fact.canonical_predicate)].append(fact)

    candidates: list[RelationshipCandidate] = []
    for block_key in sorted(blocks):
        block = sorted(
            blocks[block_key],
            key=lambda fact: (str(fact.document_id or ""), str(fact.fact_id or "")),
        )
        for index, fact_a in enumerate(block):
            for fact_b in block[index + 1 :]:
                if fact_a.fact_id is not None and fact_a.fact_id == fact_b.fact_id:
                    continue
                if cross_document_only and fact_a.document_id == fact_b.document_id:
                    continue
                candidates.append(RelationshipCandidate(fact_a=fact_a, fact_b=fact_b))
    return candidates
