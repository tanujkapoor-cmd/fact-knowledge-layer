"""Unit tests for pure deterministic fact normalization."""

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from backend.extraction import FactCandidate
from backend.reasoning import (
    CurrencyConversionError,
    ExchangeRateTable,
    TemporalGranularity,
    ValueKind,
    canonicalize_predicate,
    normalize_entity_name,
    normalize_fact,
    normalize_value,
    parse_date_range,
)


def test_entity_normalization_removes_legal_suffixes_and_punctuation() -> None:
    normalized = normalize_entity_name("The Acme & Logistics Pvt. Ltd.")

    assert normalized.comparison_key == "acme and logistics"
    assert normalized.removed_suffixes == ("pvt", "ltd")
    assert normalized.alias_applied is False


def test_entity_normalization_preserves_distinguishing_compound_name() -> None:
    parent = normalize_entity_name("Delhivery Limited")
    subsidiary = normalize_entity_name("Delhivery Corp Limited")

    assert parent.comparison_key == "delhivery"
    assert subsidiary.comparison_key == "delhivery corp"
    assert parent.comparison_key != subsidiary.comparison_key


def test_entity_aliases_are_explicit_and_deterministic() -> None:
    aliases = {"DLVRY": "Delhivery Limited"}

    first = normalize_entity_name("DLVRY", aliases)
    second = normalize_entity_name("DLVRY", aliases)

    assert first == second
    assert first.canonical_name == "Delhivery Limited"
    assert first.comparison_key == "delhivery"
    assert first.alias_applied is True


def test_predicate_normalization_only_uses_explicit_aliases() -> None:
    aliases = {"total income": "revenue"}

    assert canonicalize_predicate(" Total-Income ", aliases) == "revenue"
    assert canonicalize_predicate("operating revenue", aliases) == "operating revenue"


@pytest.mark.parametrize(
    ("value", "unit", "expected_value", "expected_unit"),
    [
        ("1.5", "kilometres", Decimal("1500.0"), "m"),
        ("1,000", "grams", Decimal("1.000"), "kg"),
        ("10", "%", Decimal("0.10"), "ratio"),
        ("2", "hours", Decimal("7200"), "s"),
    ],
)
def test_physical_unit_conversion(
    value: str,
    unit: str,
    expected_value: Decimal,
    expected_unit: str,
) -> None:
    normalized = normalize_value(value, unit=unit)

    assert normalized.kind is ValueKind.NUMERIC
    assert normalized.normalized_numeric_value == expected_value
    assert normalized.canonical_unit == expected_unit


def test_indian_and_international_scales_normalize_to_base_amounts() -> None:
    crore = normalize_value("INR 100 crore", currency="INR", unit="crore")
    million = normalize_value("INR 1,000 million", currency="INR", unit="million")

    assert crore.normalized_numeric_value == Decimal("1000000000")
    assert million.normalized_numeric_value == Decimal("1000000000")
    assert crore.canonical_currency == million.canonical_currency == "INR"
    assert crore.canonical_unit is None


def test_currency_conversion_uses_explicit_dated_rates() -> None:
    rates = ExchangeRateTable(
        base_currency="USD",
        as_of_date=date(2026, 9, 8),
        rates_to_base={"USD": Decimal("1"), "INR": Decimal("0.012")},
    )

    normalized = normalize_value(
        "INR 1,000",
        currency="INR",
        target_currency="USD",
        exchange_rates=rates,
    )

    assert normalized.normalized_numeric_value == Decimal("12.000")
    assert normalized.canonical_currency == "USD"
    assert normalized.currency_conversion_rate == Decimal("0.012")
    assert normalized.exchange_rate_date == date(2026, 9, 8)


def test_currency_conversion_fails_without_required_rate() -> None:
    with pytest.raises(CurrencyConversionError, match="exchange-rate table"):
        normalize_value("INR 1,000", currency="INR", target_currency="USD")


def test_currency_conversion_fails_when_source_currency_is_unknown() -> None:
    with pytest.raises(CurrencyConversionError, match="source currency"):
        normalize_value("1,000", target_currency="USD")


def test_currency_symbols_are_normalized_case_insensitively() -> None:
    normalized = normalize_value("CN¥ 100")

    assert normalized.canonical_currency == "CNY"


def test_text_values_are_canonicalized_without_inventing_a_number() -> None:
    normalized = normalize_value("  Strong & Stable Growth  ")

    assert normalized.kind is ValueKind.TEXT
    assert normalized.normalized_text == "strong and stable growth"
    assert normalized.normalized_numeric_value is None


def test_calendar_dates_compare_as_complete_dates_not_day_numbers() -> None:
    first = normalize_value("June 22, 2011")
    equivalent = normalize_value("22 June 2011")
    different = normalize_value("May 22, 2022")

    assert first.kind is ValueKind.TEXT
    assert first.normalized_text == equivalent.normalized_text == "2011-06-22"
    assert different.normalized_text == "2022-05-22"


def test_alphanumeric_identifiers_are_not_reduced_to_embedded_numbers() -> None:
    listed = normalize_value("L63090DL2011PLC221234")
    unlisted = normalize_value("U63090DL2011PLC221234")

    assert listed.kind is ValueKind.TEXT
    assert listed.normalized_text != unlisted.normalized_text


@pytest.mark.parametrize(
    ("scope", "expected_start", "expected_end", "granularity"),
    [
        ("FY2024", date(2023, 4, 1), date(2024, 3, 31), TemporalGranularity.FISCAL_YEAR),
        ("Fiscal 2019", date(2018, 4, 1), date(2019, 3, 31), TemporalGranularity.FISCAL_YEAR),
        (
            "Financial year 2023-24",
            date(2023, 4, 1),
            date(2024, 3, 31),
            TemporalGranularity.FISCAL_YEAR,
        ),
        ("Q4 FY24", date(2024, 1, 1), date(2024, 3, 31), TemporalGranularity.QUARTER),
        (
            "nine months ended December 31, 2023",
            date(2023, 4, 1),
            date(2023, 12, 31),
            TemporalGranularity.MULTI_MONTH,
        ),
        (
            "three months ended June 30, 2024",
            date(2024, 4, 1),
            date(2024, 6, 30),
            TemporalGranularity.QUARTER,
        ),
        (
            "year ended March 31, 2024",
            date(2023, 4, 1),
            date(2024, 3, 31),
            TemporalGranularity.YEAR,
        ),
        (
            "as of March 31, 2024",
            date(2024, 3, 31),
            date(2024, 3, 31),
            TemporalGranularity.POINT_IN_TIME,
        ),
        ("March 2024", date(2024, 3, 1), date(2024, 3, 31), TemporalGranularity.MONTH),
        ("2024", date(2024, 1, 1), date(2024, 12, 31), TemporalGranularity.YEAR),
    ],
)
def test_date_range_parsing(
    scope: str,
    expected_start: date,
    expected_end: date,
    granularity: TemporalGranularity,
) -> None:
    normalized = parse_date_range(scope)

    assert normalized.parsed is True
    assert normalized.start_date == expected_start
    assert normalized.end_date == expected_end
    assert normalized.granularity is granularity


def test_explicit_date_range_and_unknown_scope() -> None:
    date_range = parse_date_range("January 1, 2024 to March 31, 2024")
    unknown = parse_date_range("the current reporting period")

    assert date_range.start_date == date(2024, 1, 1)
    assert date_range.end_date == date(2024, 3, 31)
    assert date_range.granularity is TemporalGranularity.DATE_RANGE
    assert unknown.parsed is False
    assert unknown.granularity is TemporalGranularity.UNKNOWN


def test_normalize_fact_composes_all_pure_normalizers() -> None:
    fact = FactCandidate(
        subject="Delhivery Ltd.",
        predicate="Total Income",
        value="INR 100 crore",
        unit="crore",
        currency="INR",
        temporal_scope="FY2024",
        scope=None,
        data_vintage=None,
        evidence_quote="Delhivery reported total income of INR 100 crore in FY2024.",
        page_number=1,
    )

    normalized = normalize_fact(
        fact,
        predicate_aliases={"total income": "revenue"},
    )

    assert normalized.entity.comparison_key == "delhivery"
    assert normalized.canonical_predicate == "revenue"
    assert normalized.value.normalized_numeric_value == Decimal("1000000000")
    assert normalized.temporal_scope.start_date == date(2023, 4, 1)


def test_normalize_module_has_no_llm_sdk_imports() -> None:
    normalize_path = Path(__file__).parents[1] / "backend" / "reasoning" / "normalize.py"
    tree = ast.parse(normalize_path.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert imported_roots.isdisjoint({"openai", "anthropic", "langchain", "google"})
