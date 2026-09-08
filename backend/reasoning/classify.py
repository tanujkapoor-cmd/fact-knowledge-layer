"""Pure deterministic relationship candidate generation and classification."""

import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from decimal import Decimal
from difflib import SequenceMatcher

from backend.models import CheckOutcome, ReasoningStep, RelationshipType
from backend.reasoning.schemas import (
    AmbiguousEntityCandidate,
    ClassificationDecision,
    NormalizedFact,
    ReconciliationReason,
    RelationshipCandidate,
    ValueKind,
)

CLASSIFIER_VERSION = "classifier-v2"
_CHECKS = (
    "same_entity",
    "same_predicate",
    "normalized_value_equality",
    "rounding",
    "time_period",
    "data_vintage",
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
            trace.append(_step(order, check, CheckOutcome.SKIPPED, reason=reason))
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

    if left.canonical_unit != right.canonical_unit:
        return None
    if left.unit_dimension != right.unit_dimension:
        return None
    if left.canonical_currency != right.canonical_currency:
        return None
    assert left.normalized_numeric_value is not None
    assert right.normalized_numeric_value is not None
    return _numeric_values_equal(left.normalized_numeric_value, right.normalized_numeric_value)


def _rounding_compatible(fact_a: NormalizedFact, fact_b: NormalizedFact) -> bool:
    """Reconcile written numbers only when their explicit precision intervals overlap."""

    left = fact_a.value
    right = fact_b.value
    if left.kind is not ValueKind.NUMERIC or right.kind is not ValueKind.NUMERIC:
        return False
    if (
        left.canonical_unit != right.canonical_unit
        or left.unit_dimension != right.unit_dimension
        or left.canonical_currency != right.canonical_currency
    ):
        return False
    if left.rounding_quantum is None or right.rounding_quantum is None:
        return False
    if left.rounding_quantum == right.rounding_quantum:
        return False
    assert left.normalized_numeric_value is not None
    assert right.normalized_numeric_value is not None
    difference = abs(left.normalized_numeric_value - right.normalized_numeric_value)
    combined_half_width = (left.rounding_quantum + right.rounding_quantum) / Decimal("2")
    return difference < combined_half_width


def _display_value(fact: NormalizedFact) -> str:
    if fact.value.kind is ValueKind.NUMERIC:
        return str(fact.value.normalized_numeric_value)
    return str(fact.value.normalized_text)


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


def _period_comparison(left: object | None, right: object | None) -> str:
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


def _time_comparison(fact_a: NormalizedFact, fact_b: NormalizedFact) -> str:
    return _period_comparison(fact_a.temporal_scope, fact_b.temporal_scope)


def _vintage_comparison(fact_a: NormalizedFact, fact_b: NormalizedFact) -> str:
    return _period_comparison(fact_a.data_vintage, fact_b.data_vintage)


def _comparison_gap(fact_a: NormalizedFact, fact_b: NormalizedFact) -> str | None:
    left = fact_a.value
    right = fact_b.value
    if left.kind is not right.kind:
        return "value kinds differ"
    if left.kind is ValueKind.NUMERIC:
        if left.canonical_unit != right.canonical_unit:
            return "units are missing or cannot be converted to a common basis"
        if left.unit_dimension != right.unit_dimension:
            return "unit dimensions are missing or incompatible"
        if left.canonical_currency != right.canonical_currency:
            return "currencies were not converted to a common dated basis"
    return None


def classify_relationship(
    fact_a: NormalizedFact,
    fact_b: NormalizedFact,
    *,
    entity_match_resolved: bool = False,
) -> ClassificationDecision:
    """Classify two normalized facts using the required ordered checks."""

    trace: list[ReasoningStep] = []

    exact_entity_match = fact_a.entity.comparison_key == fact_b.entity.comparison_key
    same_entity = exact_entity_match or entity_match_resolved
    trace.append(
        _step(
            1,
            "same_entity",
            CheckOutcome.PASSED if same_entity else CheckOutcome.FAILED,
            entity_a=fact_a.entity.comparison_key,
            entity_b=fact_b.entity.comparison_key,
            match_method="canonical_key" if exact_entity_match else "bounded_llm_tiebreak",
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
            value_a=_display_value(fact_a),
            value_b=_display_value(fact_b),
        )
    )

    if values_equal:
        representation_reasons = _different_representation_reasons(fact_a, fact_b)
        if representation_reasons:
            for reason in representation_reasons:
                order = 7 if reason is ReconciliationReason.UNIT else 8
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

    rounding_compatible = _rounding_compatible(fact_a, fact_b)
    trace.append(
        _step(
            4,
            "rounding",
            CheckOutcome.PASSED if rounding_compatible else CheckOutcome.FAILED,
            quantum_a=(
                str(fact_a.value.rounding_quantum) if fact_a.value.rounding_quantum else None
            ),
            quantum_b=(
                str(fact_b.value.rounding_quantum) if fact_b.value.rounding_quantum else None
            ),
        )
    )
    if rounding_compatible:
        return _decision(
            fact_a,
            fact_b,
            RelationshipType.RECONCILED,
            trace,
            reasons=(ReconciliationReason.ROUNDING,),
            skipped_reason="the written precision intervals overlap deterministically",
        )

    time_comparison = _time_comparison(fact_a, fact_b)
    trace.append(
        _step(
            5,
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

    vintage_comparison = _vintage_comparison(fact_a, fact_b)
    trace.append(
        _step(
            6,
            "data_vintage",
            CheckOutcome.PASSED
            if vintage_comparison == "different"
            else CheckOutcome.JUDGMENT_REQUIRED
            if vintage_comparison == "unknown"
            else CheckOutcome.FAILED,
            comparison=vintage_comparison,
        )
    )
    if vintage_comparison == "different":
        return _decision(
            fact_a,
            fact_b,
            RelationshipType.RECONCILED,
            trace,
            reasons=(ReconciliationReason.DATA_VINTAGE,),
            skipped_reason="different source-data vintages explain the different values",
        )

    trace.append(
        _step(
            7,
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
            8,
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
            9,
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
    if time_comparison == "unknown" or vintage_comparison == "unknown" or scope_unknown or gap:
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
    resolved_entity_pair_ids: set[str] | None = None,
    entity_similarities: dict[str, float] | None = None,
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
    by_id = {str(fact.fact_id): fact for fact in facts if fact.fact_id is not None}
    for pair_id in sorted(resolved_entity_pair_ids or set()):
        left_id, separator, right_id = pair_id.partition("::")
        if not separator or left_id not in by_id or right_id not in by_id:
            continue
        fact_a, fact_b = by_id[left_id], by_id[right_id]
        if fact_a.canonical_predicate != fact_b.canonical_predicate:
            continue
        if cross_document_only and fact_a.document_id == fact_b.document_id:
            continue
        candidates.append(
            RelationshipCandidate(
                fact_a=fact_a,
                fact_b=fact_b,
                entity_match_resolved=True,
                entity_similarity=(entity_similarities or {}).get(pair_id),
            )
        )
    return candidates


def find_ambiguous_entity_candidates(
    facts: Sequence[NormalizedFact],
    *,
    lower_similarity: float = 0.82,
    upper_similarity: float = 0.97,
    max_pairs: int = 20,
    cross_document_only: bool = True,
) -> list[AmbiguousEntityCandidate]:
    """Return at most ``max_pairs`` near-name ties sharing an exact predicate key."""

    if not 0 <= lower_similarity < upper_similarity <= 1:
        raise ValueError("entity similarity bounds must satisfy 0 <= lower < upper <= 1")
    if max_pairs < 0:
        raise ValueError("max_pairs must be non-negative")

    ordered = sorted(
        (fact for fact in facts if fact.fact_id is not None),
        key=lambda fact: (fact.canonical_predicate, str(fact.document_id), str(fact.fact_id)),
    )
    matches: list[AmbiguousEntityCandidate] = []
    for index, fact_a in enumerate(ordered):
        for fact_b in ordered[index + 1 :]:
            if fact_a.canonical_predicate != fact_b.canonical_predicate:
                continue
            if cross_document_only and fact_a.document_id == fact_b.document_id:
                continue
            if fact_a.entity.comparison_key == fact_b.entity.comparison_key:
                continue
            similarity = SequenceMatcher(
                None,
                fact_a.entity.comparison_key,
                fact_b.entity.comparison_key,
            ).ratio()
            if not lower_similarity <= similarity < upper_similarity:
                continue
            left_id, right_id = sorted((str(fact_a.fact_id), str(fact_b.fact_id)))
            matches.append(
                AmbiguousEntityCandidate(
                    pair_id=f"{left_id}::{right_id}",
                    fact_a=fact_a,
                    fact_b=fact_b,
                    similarity=similarity,
                )
            )

    matches.sort(key=lambda item: (-item.similarity, item.pair_id))
    return matches[:max_pairs]
