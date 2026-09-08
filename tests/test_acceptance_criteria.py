"""Requirement-level tests for the deterministic reasoning boundary."""

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.models import CheckOutcome, RelationshipType
from backend.reasoning import (
    ExchangeRateTable,
    ReconciliationReason,
    block_relationship_candidates,
    classify_relationship,
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
    target_currency: str | None = None,
    rates: ExchangeRateTable | None = None,
):
    return normalize_fact(
        SimpleNamespace(
            id=uuid4(),
            document_id=uuid4(),
            subject=entity,
            predicate=predicate,
            value=value,
            unit=unit,
            currency=currency,
            temporal_scope=time,
            scope=scope,
        ),
        target_currency=target_currency,
        exchange_rates=rates,
    )


@pytest.mark.parametrize(
    ("left", "right", "expected", "reason"),
    [
        (_fact("100"), _fact("100"), RelationshipType.CORROBORATES, None),
        (_fact("100"), _fact("120"), RelationshipType.CONTRADICTS, None),
        (
            _fact("100", time="FY2023"),
            _fact("120", time="FY2024"),
            RelationshipType.RECONCILED,
            ReconciliationReason.TIME_PERIOD,
        ),
        (
            _fact("1", unit="kilometre"),
            _fact("1000", unit="metres"),
            RelationshipType.RECONCILED,
            ReconciliationReason.UNIT,
        ),
        (
            _fact("100", scope="India"),
            _fact("120", scope="Global"),
            RelationshipType.RECONCILED,
            ReconciliationReason.SCOPE,
        ),
        (
            _fact("1", unit="box"),
            _fact("1", unit="pallet"),
            RelationshipType.UNCERTAIN,
            None,
        ),
    ],
)
def test_required_classifier_outcomes_have_complete_ordered_traces(
    left,
    right,
    expected: RelationshipType,
    reason: ReconciliationReason | None,
) -> None:
    decision = classify_relationship(left, right)

    assert decision.classification is expected
    assert [step.order for step in decision.reasoning_trace] == list(range(1, 10))
    assert [step.check for step in decision.reasoning_trace] == [
        "same_entity",
        "same_predicate",
        "normalized_value_equality",
        "rounding",
        "time_period",
        "data_vintage",
        "unit",
        "currency",
        "scope",
    ]
    if reason:
        assert reason in decision.reconciliation_reasons
        reason_step = next(step for step in decision.reasoning_trace if step.check == reason.value)
        assert reason_step.outcome is CheckOutcome.PASSED


def test_currency_reconciliation_uses_an_explicit_dated_rate() -> None:
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


def test_zero_is_preserved_in_machine_readable_trace() -> None:
    decision = classify_relationship(_fact("0"), _fact("0"))
    equality = decision.reasoning_trace[2]

    assert equality.details["value_a"] == "0"
    assert equality.details["value_b"] == "0"


def test_text_and_mixed_value_branches_are_explicit() -> None:
    equal_text = classify_relationship(_fact("Strong growth"), _fact("strong growth"))
    different_text = classify_relationship(_fact("Strong growth"), _fact("Weak growth"))
    mixed = classify_relationship(_fact("100"), _fact("Not disclosed"))

    assert equal_text.classification is RelationshipType.CORROBORATES
    assert equal_text.reasoning_trace[2].details["value_a"] == "strong growth"
    assert different_text.classification is RelationshipType.CONTRADICTS
    assert mixed.classification is RelationshipType.UNCERTAIN


def test_missing_and_unparsed_time_context_produce_safe_outcomes() -> None:
    no_time = classify_relationship(_fact("100", time=None), _fact("120", time=None))
    one_missing = classify_relationship(_fact("100", time=None), _fact("120"))
    same_unknown = classify_relationship(
        _fact("100", time="current period"),
        _fact("120", time="CURRENT PERIOD"),
    )
    different_unknown = classify_relationship(
        _fact("100", time="current period"),
        _fact("120", time="latest period"),
    )

    assert no_time.classification is RelationshipType.CONTRADICTS
    assert one_missing.classification is RelationshipType.UNCERTAIN
    assert same_unknown.classification is RelationshipType.CONTRADICTS
    assert different_unknown.classification is RelationshipType.UNCERTAIN


def test_unconverted_currency_and_partial_scope_are_uncertain() -> None:
    currency = classify_relationship(
        _fact("100", currency="INR"),
        _fact("100", currency="USD"),
    )
    scope = classify_relationship(
        _fact("100", scope="India"),
        _fact("120", scope=None),
    )

    assert currency.classification is RelationshipType.UNCERTAIN
    assert scope.classification is RelationshipType.UNCERTAIN


def test_inconsistent_unit_dimensions_cannot_be_compared() -> None:
    left = _fact("1", unit="metre")
    right = _fact("1", unit="metre")
    right = right.model_copy(
        update={
            "value": right.value.model_copy(update={"unit_dimension": "mass"}),
        }
    )

    assert classify_relationship(left, right).classification is RelationshipType.UNCERTAIN


def test_candidate_blocker_skips_duplicates_and_can_include_same_document() -> None:
    document_id = uuid4()
    shared_fact_id = uuid4()
    first = _fact("100").model_copy(update={"document_id": document_id, "fact_id": shared_fact_id})
    duplicate = _fact("120").model_copy(
        update={"document_id": document_id, "fact_id": shared_fact_id}
    )
    distinct = _fact("130").model_copy(update={"document_id": document_id})

    assert block_relationship_candidates([first, duplicate, distinct]) == []
    same_document = block_relationship_candidates(
        [first, distinct],
        cross_document_only=False,
    )
    assert len(same_document) == 1


def test_all_reasoning_modules_are_free_of_llm_sdk_imports() -> None:
    reasoning_dir = Path(__file__).parents[1] / "backend" / "reasoning"
    forbidden = {"openai", "anthropic", "langchain", "google"}

    for path in reasoning_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        assert imported_roots.isdisjoint(forbidden), path.name
