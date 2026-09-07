"""Pure metric calculations for hand-labeled extraction and relationships."""

import re
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from backend.models import RelationshipType
from backend.reasoning import (
    canonicalize_predicate,
    normalize_entity_name,
    normalize_value,
    parse_date_range,
)
from evaluation.schemas import (
    EvaluationFact,
    EvaluationResults,
    ExtractionMetrics,
    GroundTruthDataset,
    PredictionDataset,
    RelationshipMetrics,
)

MISSING_LABEL = "missing"
RELATIONSHIP_LABELS = [relationship.value for relationship in RelationshipType]


def _clean(text: str | None) -> str | None:
    if text is None:
        return None
    return " ".join(re.findall(r"[^\W_]+", text.casefold()))


def _fact_signature(fact: EvaluationFact) -> tuple[object, ...]:
    normalized_value = normalize_value(
        fact.value,
        unit=fact.unit,
        currency=fact.currency,
    )
    if normalized_value.normalized_numeric_value is not None:
        value_key: object = (
            "numeric",
            str(normalized_value.normalized_numeric_value.normalize()),
            normalized_value.canonical_unit,
            normalized_value.canonical_currency,
        )
    else:
        value_key = ("text", normalized_value.normalized_text)

    temporal = parse_date_range(fact.temporal_scope) if fact.temporal_scope else None
    if temporal and temporal.parsed:
        temporal_key: object = (str(temporal.start_date), str(temporal.end_date))
    else:
        temporal_key = _clean(fact.temporal_scope)

    return (
        _clean(fact.document_key),
        fact.physical_page_number,
        normalize_entity_name(fact.subject).comparison_key,
        canonicalize_predicate(fact.predicate),
        value_key,
        temporal_key,
    )


def _in_scope(fact: EvaluationFact, ground_truth: GroundTruthDataset) -> bool:
    fact_document = _clean(fact.document_key)
    for scope in ground_truth.scope:
        if _clean(scope.document_key) != fact_document:
            continue
        return scope.physical_pages is None or fact.physical_page_number in scope.physical_pages
    return False


def _match_facts(
    ground_truth: GroundTruthDataset,
    predictions: PredictionDataset,
) -> tuple[dict[str, str], list[tuple[EvaluationFact, EvaluationFact]], int, int, int]:
    scoped_predictions = [fact for fact in predictions.facts if _in_scope(fact, ground_truth)]
    predictions_by_signature: dict[tuple[object, ...], list[EvaluationFact]] = defaultdict(list)
    for fact in scoped_predictions:
        predictions_by_signature[_fact_signature(fact)].append(fact)

    mapping: dict[str, str] = {}
    matches: list[tuple[EvaluationFact, EvaluationFact]] = []
    for expected in ground_truth.facts:
        candidates = predictions_by_signature[_fact_signature(expected)]
        if not candidates:
            continue
        predicted = candidates.pop(0)
        mapping[expected.id] = predicted.id
        matches.append((expected, predicted))

    true_positives = len(matches)
    false_negatives = len(ground_truth.facts) - true_positives
    false_positives = len(scoped_predictions) - true_positives
    return mapping, matches, true_positives, false_positives, false_negatives


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _relationship_lookup(relationships: Iterable[Any]) -> dict[frozenset[str], str]:
    return {
        frozenset((relationship.fact_a_id, relationship.fact_b_id)): (
            relationship.classification.value
        )
        for relationship in relationships
    }


def evaluate(
    ground_truth: GroundTruthDataset,
    predictions: PredictionDataset,
) -> EvaluationResults:
    """Compute scoped extraction precision/recall and pair-label confusion."""

    mapping, matches, true_positives, false_positives, false_negatives = _match_facts(
        ground_truth,
        predictions,
    )
    exact_quotes = sum(
        expected.evidence_quote == predicted.evidence_quote for expected, predicted in matches
    )
    extraction = ExtractionMetrics(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=_safe_ratio(true_positives, true_positives + false_positives),
        recall=_safe_ratio(true_positives, true_positives + false_negatives),
        exact_evidence_quote_rate=(_safe_ratio(exact_quotes, len(matches)) if matches else None),
    )

    prediction_labels = [*RELATIONSHIP_LABELS, MISSING_LABEL]
    matrix = [[0 for _ in prediction_labels] for _ in RELATIONSHIP_LABELS]
    expected_index = {label: index for index, label in enumerate(RELATIONSHIP_LABELS)}
    predicted_index = {label: index for index, label in enumerate(prediction_labels)}
    predicted_relationships = _relationship_lookup(predictions.relationships)
    correct = 0
    missing = 0

    for expected in ground_truth.relationships:
        expected_label = expected.classification.value
        mapped_a = mapping.get(expected.fact_a_id)
        mapped_b = mapping.get(expected.fact_b_id)
        predicted_label = MISSING_LABEL
        if mapped_a and mapped_b:
            predicted_label = predicted_relationships.get(
                frozenset((mapped_a, mapped_b)),
                MISSING_LABEL,
            )
        matrix[expected_index[expected_label]][predicted_index[predicted_label]] += 1
        correct += predicted_label == expected_label
        missing += predicted_label == MISSING_LABEL

    evaluated_pairs = len(ground_truth.relationships)
    relationships = RelationshipMetrics(
        labels=RELATIONSHIP_LABELS,
        prediction_labels=prediction_labels,
        confusion_matrix=matrix,
        accuracy=_safe_ratio(correct, evaluated_pairs),
        evaluated_pairs=evaluated_pairs,
        missing_predictions=missing,
    )
    return EvaluationResults(extraction=extraction, relationships=relationships)
