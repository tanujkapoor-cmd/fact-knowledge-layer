"""Branch tests for deterministic relationship classification."""

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from backend.models import RelationshipType
from backend.reasoning import (
    ExchangeRateTable,
    ReconciliationReason,
    block_relationship_candidates,
    classify_relationship,
    find_ambiguous_entity_candidates,
    normalize_fact,
)


def _fact(
    value: str,
    *,
    entity: str = "Acme Ltd.",
    predicate: str = "Revenue",
    unit: str | None = None,
    currency: str | None = None,
    time: str | None = "FY2024",
    scope: str | None = None,
    document_id=None,
    target_currency: str | None = None,
    rates: ExchangeRateTable | None = None,
    data_vintage: str | None = None,
):
    source = SimpleNamespace(
        id=uuid4(),
        document_id=document_id or uuid4(),
        subject=entity,
        predicate=predicate,
        value=value,
        unit=unit,
        currency=currency,
        temporal_scope=time,
        scope=scope,
        data_vintage=data_vintage,
    )
    return normalize_fact(source, target_currency=target_currency, exchange_rates=rates)


def test_equal_normalized_facts_corroborate() -> None:
    decision = classify_relationship(_fact("100"), _fact("100"))

    assert decision.classification is RelationshipType.CORROBORATES
    assert decision.reconciliation_reasons == ()
    assert [step.order for step in decision.reasoning_trace] == list(range(1, 10))


def test_same_context_with_different_values_contradicts() -> None:
    decision = classify_relationship(_fact("100"), _fact("120"))

    assert decision.classification is RelationshipType.CONTRADICTS


def test_different_periods_reconcile_different_values() -> None:
    decision = classify_relationship(_fact("100", time="FY2023"), _fact("120", time="FY2024"))

    assert decision.classification is RelationshipType.RECONCILED
    assert decision.reconciliation_reasons == (ReconciliationReason.TIME_PERIOD,)


def test_equivalent_units_are_reconciled() -> None:
    decision = classify_relationship(
        _fact("1", unit="kilometre"),
        _fact("1000", unit="metres"),
    )

    assert decision.classification is RelationshipType.RECONCILED
    assert decision.reconciliation_reasons == (ReconciliationReason.UNIT,)


def test_equivalent_currencies_are_reconciled_with_explicit_rates() -> None:
    rates = ExchangeRateTable(
        base_currency="USD",
        as_of_date=date(2026, 9, 8),
        rates_to_base={"USD": Decimal("1"), "INR": Decimal("0.012")},
    )
    decision = classify_relationship(
        _fact("INR 1000", currency="INR", target_currency="USD", rates=rates),
        _fact("USD 12", currency="USD", target_currency="USD", rates=rates),
    )

    assert decision.classification is RelationshipType.RECONCILED
    assert decision.reconciliation_reasons == (ReconciliationReason.CURRENCY,)


def test_different_scopes_reconcile_different_values() -> None:
    decision = classify_relationship(
        _fact("100", scope="India"),
        _fact("120", scope="Global"),
    )

    assert decision.classification is RelationshipType.RECONCILED
    assert decision.reconciliation_reasons == (ReconciliationReason.SCOPE,)


def test_different_data_vintages_reconcile_different_values() -> None:
    decision = classify_relationship(
        _fact("6.4", data_vintage="as of 30 April 2024"),
        _fact("6.5", data_vintage="as of 31 May 2024"),
    )

    assert decision.classification is RelationshipType.RECONCILED
    assert decision.reconciliation_reasons == (ReconciliationReason.DATA_VINTAGE,)


def test_overlapping_written_precision_reconciles_rounding() -> None:
    decision = classify_relationship(
        _fact("12.7", unit="percent"),
        _fact("13", unit="percent"),
    )

    assert decision.classification is RelationshipType.RECONCILED
    assert decision.reconciliation_reasons == (ReconciliationReason.ROUNDING,)


def test_equal_precision_does_not_hide_a_real_difference_as_rounding() -> None:
    decision = classify_relationship(_fact("100"), _fact("101"))

    assert decision.classification is RelationshipType.CONTRADICTS


def test_incompatible_units_are_uncertain() -> None:
    decision = classify_relationship(
        _fact("1", unit="kilometre"),
        _fact("1", unit="kilogram"),
    )

    assert decision.classification is RelationshipType.UNCERTAIN


def test_unmatched_entity_or_predicate_is_uncertain() -> None:
    entity_decision = classify_relationship(_fact("100"), _fact("100", entity="Beta Ltd."))
    predicate_decision = classify_relationship(_fact("100"), _fact("100", predicate="Profit"))

    assert entity_decision.classification is RelationshipType.UNCERTAIN
    assert predicate_decision.classification is RelationshipType.UNCERTAIN


def test_candidate_blocking_uses_entity_predicate_and_cross_document() -> None:
    document_a = uuid4()
    document_b = uuid4()
    facts = [
        _fact("100", document_id=document_a),
        _fact("110", document_id=document_b),
        _fact("90", predicate="Profit", document_id=document_b),
        _fact("105", document_id=document_a),
    ]

    candidates = block_relationship_candidates(facts)

    assert len(candidates) == 2
    assert all(pair.fact_a.document_id != pair.fact_b.document_id for pair in candidates)


def test_ambiguous_entity_candidates_are_bounded_and_require_explicit_resolution() -> None:
    facts = [
        _fact("100", entity="Acme Logistics", document_id=uuid4()),
        _fact("100", entity="Acme Logistic", document_id=uuid4()),
        _fact("100", entity="Completely Different", document_id=uuid4()),
    ]

    ambiguous = find_ambiguous_entity_candidates(facts, max_pairs=1)
    assert len(ambiguous) == 1
    resolved = block_relationship_candidates(
        facts,
        resolved_entity_pair_ids={ambiguous[0].pair_id},
        entity_similarities={ambiguous[0].pair_id: ambiguous[0].similarity},
    )
    decision = classify_relationship(
        resolved[0].fact_a,
        resolved[0].fact_b,
        entity_match_resolved=resolved[0].entity_match_resolved,
    )

    assert decision.classification is RelationshipType.CORROBORATES
    assert decision.reasoning_trace[0].details["match_method"] == "bounded_llm_tiebreak"


def test_classifier_module_has_no_llm_sdk_imports() -> None:
    path = Path(__file__).parents[1] / "backend" / "reasoning" / "classify.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert imported_roots.isdisjoint({"openai", "anthropic", "langchain", "google"})
