"""Pure deterministic normalization for cross-document fact comparison.

This module performs no I/O and contains no LLM calls. Currency conversion is
only performed with an explicit, dated exchange-rate table supplied by the
caller.
"""

import calendar
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

from backend.reasoning.schemas import (
    EntityNormalization,
    ExchangeRateTable,
    NormalizedFact,
    NormalizedTemporalScope,
    NormalizedValue,
    TemporalGranularity,
    ValueKind,
)

NORMALIZATION_VERSION = "normalization-v1"


class CurrencyConversionError(ValueError):
    """An explicit currency conversion lacks a valid deterministic rate."""


class NormalizableFact(Protocol):
    """Structural input accepted by `normalize_fact`."""

    subject: str
    predicate: str
    value: str
    unit: str | None
    currency: str | None
    temporal_scope: Any
    scope: str | None
    data_vintage: Any


@dataclass(frozen=True, slots=True)
class _UnitSpec:
    canonical_unit: str | None
    dimension: str | None
    factor: Decimal


_CORPORATE_SUFFIXES = {
    "co",
    "company",
    "corp",
    "corporation",
    "inc",
    "incorporated",
    "llc",
    "llp",
    "limited",
    "ltd",
    "plc",
    "private",
    "pvt",
}
_COMPOUND_PREFIX_SUFFIXES = {"private", "pvt"}

_SCALE_FACTORS = {
    "hundred": Decimal("100"),
    "thousand": Decimal("1000"),
    "k": Decimal("1000"),
    "lakh": Decimal("100000"),
    "lac": Decimal("100000"),
    "million": Decimal("1000000"),
    "mn": Decimal("1000000"),
    "crore": Decimal("10000000"),
    "cr": Decimal("10000000"),
    "billion": Decimal("1000000000"),
    "bn": Decimal("1000000000"),
    "trillion": Decimal("1000000000000"),
    "tn": Decimal("1000000000000"),
}

_UNIT_ALIASES: dict[str, _UnitSpec] = {
    "%": _UnitSpec("ratio", "ratio", Decimal("0.01")),
    "percent": _UnitSpec("ratio", "ratio", Decimal("0.01")),
    "percentage": _UnitSpec("ratio", "ratio", Decimal("0.01")),
    "ratio": _UnitSpec("ratio", "ratio", Decimal("1")),
    "millimeter": _UnitSpec("m", "length", Decimal("0.001")),
    "millimeters": _UnitSpec("m", "length", Decimal("0.001")),
    "mm": _UnitSpec("m", "length", Decimal("0.001")),
    "centimeter": _UnitSpec("m", "length", Decimal("0.01")),
    "centimeters": _UnitSpec("m", "length", Decimal("0.01")),
    "cm": _UnitSpec("m", "length", Decimal("0.01")),
    "meter": _UnitSpec("m", "length", Decimal("1")),
    "meters": _UnitSpec("m", "length", Decimal("1")),
    "metre": _UnitSpec("m", "length", Decimal("1")),
    "metres": _UnitSpec("m", "length", Decimal("1")),
    "m": _UnitSpec("m", "length", Decimal("1")),
    "kilometer": _UnitSpec("m", "length", Decimal("1000")),
    "kilometers": _UnitSpec("m", "length", Decimal("1000")),
    "kilometre": _UnitSpec("m", "length", Decimal("1000")),
    "kilometres": _UnitSpec("m", "length", Decimal("1000")),
    "km": _UnitSpec("m", "length", Decimal("1000")),
    "inch": _UnitSpec("m", "length", Decimal("0.0254")),
    "inches": _UnitSpec("m", "length", Decimal("0.0254")),
    "foot": _UnitSpec("m", "length", Decimal("0.3048")),
    "feet": _UnitSpec("m", "length", Decimal("0.3048")),
    "ft": _UnitSpec("m", "length", Decimal("0.3048")),
    "mile": _UnitSpec("m", "length", Decimal("1609.344")),
    "miles": _UnitSpec("m", "length", Decimal("1609.344")),
    "milligram": _UnitSpec("kg", "mass", Decimal("0.000001")),
    "milligrams": _UnitSpec("kg", "mass", Decimal("0.000001")),
    "mg": _UnitSpec("kg", "mass", Decimal("0.000001")),
    "gram": _UnitSpec("kg", "mass", Decimal("0.001")),
    "grams": _UnitSpec("kg", "mass", Decimal("0.001")),
    "g": _UnitSpec("kg", "mass", Decimal("0.001")),
    "kilogram": _UnitSpec("kg", "mass", Decimal("1")),
    "kilograms": _UnitSpec("kg", "mass", Decimal("1")),
    "kg": _UnitSpec("kg", "mass", Decimal("1")),
    "tonne": _UnitSpec("kg", "mass", Decimal("1000")),
    "tonnes": _UnitSpec("kg", "mass", Decimal("1000")),
    "metric ton": _UnitSpec("kg", "mass", Decimal("1000")),
    "metric tons": _UnitSpec("kg", "mass", Decimal("1000")),
    "second": _UnitSpec("s", "duration", Decimal("1")),
    "seconds": _UnitSpec("s", "duration", Decimal("1")),
    "sec": _UnitSpec("s", "duration", Decimal("1")),
    "minute": _UnitSpec("s", "duration", Decimal("60")),
    "minutes": _UnitSpec("s", "duration", Decimal("60")),
    "min": _UnitSpec("s", "duration", Decimal("60")),
    "hour": _UnitSpec("s", "duration", Decimal("3600")),
    "hours": _UnitSpec("s", "duration", Decimal("3600")),
    "hr": _UnitSpec("s", "duration", Decimal("3600")),
    "day": _UnitSpec("s", "duration", Decimal("86400")),
    "days": _UnitSpec("s", "duration", Decimal("86400")),
}

_CURRENCY_ALIASES = {
    "₹": "INR",
    "rs": "INR",
    "rs.": "INR",
    "inr": "INR",
    "$": "USD",
    "us$": "USD",
    "usd": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
    "¥": "JPY",
    "jpy": "JPY",
    "cn¥": "CNY",
    "cny": "CNY",
}

_NUMBER_PATTERN = re.compile(
    r"(?P<parenthesized>\()?\s*(?P<sign>[+-])?\s*"
    r"(?P<number>(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d+)?)\s*\)?"
)
_WORD_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)
_MONTHS = {
    name.casefold(): number
    for number in range(1, 13)
    for name in (calendar.month_name[number], calendar.month_abbr[number])
}
_MONTH_PATTERN = "|".join(sorted((re.escape(name) for name in _MONTHS), key=len, reverse=True))
_DATE_PATTERNS = (
    re.compile(
        rf"(?P<month>{_MONTH_PATTERN})\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?[,]?\s+"
        r"(?P<year>\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?P<day>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<month>{_MONTH_PATTERN})[,]?\s+"
        r"(?P<year>\d{4})",
        re.IGNORECASE,
    ),
    re.compile(r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})"),
)


def _comparison_key(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold().replace("&", " and ")
    tokens = _WORD_PATTERN.findall(normalized)
    return " ".join(tokens)


def normalize_entity_name(
    name: str,
    aliases: Mapping[str, str] | None = None,
) -> EntityNormalization:
    """Canonicalize an entity and optionally apply an explicit alias map."""

    if not name.strip():
        raise ValueError("entity name must not be blank")

    original_key = _comparison_key(name)
    tokens = original_key.split()
    if tokens and tokens[0] == "the":
        tokens.pop(0)

    removed_suffixes: list[str] = []
    if tokens and tokens[-1] in _CORPORATE_SUFFIXES:
        removed_suffixes.insert(0, tokens.pop())
        if tokens and tokens[-1] in _COMPOUND_PREFIX_SUFFIXES:
            removed_suffixes.insert(0, tokens.pop())

    comparison_key = " ".join(tokens) or original_key
    alias_index = {
        _comparison_key(alias): canonical.strip() for alias, canonical in (aliases or {}).items()
    }
    alias_target = alias_index.get(original_key) or alias_index.get(comparison_key)
    if alias_target:
        canonical_name = alias_target
        alias_key = _comparison_key(alias_target)
        alias_tokens = alias_key.split()
        if alias_tokens and alias_tokens[-1] in _CORPORATE_SUFFIXES:
            alias_tokens.pop()
            if alias_tokens and alias_tokens[-1] in _COMPOUND_PREFIX_SUFFIXES:
                alias_tokens.pop()
        comparison_key = " ".join(alias_tokens) or alias_key
    else:
        canonical_name = comparison_key

    return EntityNormalization(
        original_name=name,
        canonical_name=canonical_name,
        comparison_key=comparison_key,
        alias_applied=alias_target is not None,
        removed_suffixes=tuple(removed_suffixes),
    )


def canonicalize_predicate(
    predicate: str,
    aliases: Mapping[str, str] | None = None,
) -> str:
    """Create a stable comparison key without guessing semantic equivalence."""

    if not predicate.strip():
        raise ValueError("predicate must not be blank")
    key = _comparison_key(predicate)
    alias_index = {
        _comparison_key(alias): _comparison_key(canonical)
        for alias, canonical in (aliases or {}).items()
    }
    return alias_index.get(key, key)


def _canonical_currency(currency: str | None, value: str) -> str | None:
    if currency and currency.strip():
        cleaned = currency.strip()
        alias = _CURRENCY_ALIASES.get(cleaned.casefold())
        if alias:
            return alias
        if re.fullmatch(r"[A-Za-z]{3}", cleaned):
            return cleaned.upper()

    casefolded_value = value.casefold()
    for token, code in sorted(
        _CURRENCY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if token.isalpha():
            if re.search(rf"\b{re.escape(token)}\b", value, re.IGNORECASE):
                return code
        elif token in casefolded_value:
            return code
    return None


def _parse_number(value: str) -> Decimal | None:
    match = _NUMBER_PATTERN.search(value)
    if not match:
        return None
    try:
        number = Decimal(match.group("number").replace(",", ""))
    except InvalidOperation:
        return None
    if match.group("sign") == "-" or match.group("parenthesized"):
        return -number
    return number


def _parse_full_date_value(value: str) -> date | None:
    """Parse a value only when the entire field is a calendar date."""

    stripped = value.strip()
    for pattern in _DATE_PATTERNS:
        match = pattern.fullmatch(stripped)
        if not match:
            continue
        month_value = match.group("month")
        month = int(month_value) if month_value.isdigit() else _MONTHS[month_value.casefold()]
        try:
            return date(int(match.group("year")), month, int(match.group("day")))
        except ValueError:
            return None
    return None


def _numeric_quantum(value: str) -> Decimal | None:
    """Return the resolution implied by the written numeric literal."""

    match = _NUMBER_PATTERN.search(value)
    if not match:
        return None
    literal = match.group("number").replace(",", "")
    decimal_places = len(literal.partition(".")[2]) if "." in literal else 0
    return Decimal(1).scaleb(-decimal_places)


def _normalized_unit_text(unit: str | None) -> str | None:
    if not unit or not unit.strip():
        return None
    return _comparison_key(unit.replace("%", " percent "))


def _find_scale(value: str, unit: str | None) -> tuple[str | None, Decimal]:
    searchable = f"{unit or ''} {value}".casefold()
    for scale, factor in sorted(
        _SCALE_FACTORS.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if re.search(rf"(?<!\w){re.escape(scale)}s?(?!\w)", searchable):
            return scale, factor
    return None, Decimal("1")


def _find_unit(value: str, unit: str | None, scale: str | None) -> tuple[str | None, _UnitSpec]:
    candidates = [_normalized_unit_text(unit), _normalized_unit_text(value)]
    for candidate in candidates:
        if not candidate:
            continue
        for alias, spec in sorted(
            _UNIT_ALIASES.items(), key=lambda item: len(item[0]), reverse=True
        ):
            normalized_alias = _comparison_key(alias.replace("%", " percent "))
            if re.search(rf"(?<!\w){re.escape(normalized_alias)}(?!\w)", candidate):
                return alias, spec

    if unit:
        custom = _normalized_unit_text(unit)
        if scale and custom:
            custom = re.sub(rf"(?<!\w){re.escape(scale)}s?(?!\w)", "", custom).strip()
        currency_words = "|".join(re.escape(key) for key in _CURRENCY_ALIASES if key.isalpha())
        if custom:
            custom = re.sub(rf"\b(?:{currency_words})\b", "", custom, flags=re.IGNORECASE)
            custom = " ".join(custom.split())
        if custom:
            return custom, _UnitSpec(custom, "custom", Decimal("1"))

    return None, _UnitSpec(None, None, Decimal("1"))


def normalize_value(
    value: str,
    *,
    unit: str | None = None,
    currency: str | None = None,
    target_currency: str | None = None,
    exchange_rates: ExchangeRateTable | None = None,
) -> NormalizedValue:
    """Normalize numeric scale, unit, and optional currency conversion."""

    source_currency = _canonical_currency(currency, value)
    scale_name, scale_factor = _find_scale(value, unit)
    _, unit_spec = _find_unit(value, unit, scale_name)
    parsed_date = _parse_full_date_value(value)
    has_untyped_letters_and_digits = (
        source_currency is None
        and unit_spec.canonical_unit is None
        and re.search(r"[A-Za-z]", value) is not None
        and re.search(r"\d", value) is not None
    )

    if parsed_date is not None or has_untyped_letters_and_digits:
        normalized_text = (
            parsed_date.isoformat() if parsed_date is not None else _comparison_key(value)
        )
        return NormalizedValue(
            kind=ValueKind.TEXT,
            original_value=value,
            normalized_text=normalized_text,
            original_unit=unit,
            canonical_unit=unit_spec.canonical_unit,
            unit_dimension=unit_spec.dimension,
            original_currency=currency,
            canonical_currency=source_currency,
        )

    numeric_value = _parse_number(value)
    numeric_quantum = _numeric_quantum(value)

    if numeric_value is None:
        normalized_text = _comparison_key(value) or unicodedata.normalize("NFKC", value).casefold()
        return NormalizedValue(
            kind=ValueKind.TEXT,
            original_value=value,
            normalized_text=normalized_text,
            original_unit=unit,
            canonical_unit=unit_spec.canonical_unit,
            unit_dimension=unit_spec.dimension,
            original_currency=currency,
            canonical_currency=source_currency,
        )

    normalized_number = numeric_value * scale_factor * unit_spec.factor
    rounding_quantum = (
        numeric_quantum * scale_factor * unit_spec.factor if numeric_quantum else None
    )
    canonical_currency = source_currency
    currency_rate: Decimal | None = None
    exchange_rate_date: date | None = None

    if target_currency and not source_currency:
        raise CurrencyConversionError("currency conversion requires a source currency")

    if target_currency and source_currency:
        target = _canonical_currency(target_currency, target_currency)
        if target is None:
            raise CurrencyConversionError(f"unsupported target currency: {target_currency}")
        if target != source_currency:
            if exchange_rates is None:
                raise CurrencyConversionError("currency conversion requires an exchange-rate table")
            source_rate = exchange_rates.rates_to_base.get(source_currency)
            target_rate = exchange_rates.rates_to_base.get(target)
            if source_rate is None or target_rate is None:
                raise CurrencyConversionError(
                    f"missing deterministic rate for {source_currency} or {target}"
                )
            currency_rate = source_rate / target_rate
            normalized_number *= currency_rate
            if rounding_quantum is not None:
                rounding_quantum *= currency_rate
            exchange_rate_date = exchange_rates.as_of_date
        canonical_currency = target

    return NormalizedValue(
        kind=ValueKind.NUMERIC,
        original_value=value,
        original_numeric_value=numeric_value,
        normalized_numeric_value=normalized_number,
        original_unit=unit,
        canonical_unit=unit_spec.canonical_unit,
        unit_dimension=unit_spec.dimension,
        scale_factor=scale_factor,
        unit_conversion_factor=unit_spec.factor,
        original_currency=currency,
        canonical_currency=canonical_currency,
        currency_conversion_rate=currency_rate,
        exchange_rate_date=exchange_rate_date,
        rounding_quantum=rounding_quantum,
    )


def _expand_short_year(year: int) -> int:
    if year >= 100:
        return year
    return 2000 + year if year < 70 else 1900 + year


def _month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _shift_months(value: date, months: int) -> date:
    absolute_month = value.year * 12 + value.month - 1 + months
    year, zero_based_month = divmod(absolute_month, 12)
    month = zero_based_month + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def _period_start_for_months(end_date: date, months: int) -> date:
    if end_date == _month_end(end_date.year, end_date.month):
        end_month_start = date(end_date.year, end_date.month, 1)
        return _shift_months(end_month_start, -(months - 1))
    return _shift_months(end_date, -months) + timedelta(days=1)


def _dates_in_text(text: str) -> list[tuple[int, date]]:
    found: list[tuple[int, date]] = []
    for pattern in _DATE_PATTERNS:
        for match in pattern.finditer(text):
            month_value = match.group("month")
            month = int(month_value) if month_value.isdigit() else _MONTHS[month_value.casefold()]
            try:
                parsed = date(int(match.group("year")), month, int(match.group("day")))
            except ValueError:
                continue
            found.append((match.start(), parsed))
    return sorted(set(found), key=lambda item: item[0])


def _temporal_result(
    raw: str,
    start: date,
    end: date,
    granularity: TemporalGranularity,
) -> NormalizedTemporalScope:
    return NormalizedTemporalScope(
        original_text=raw,
        start_date=start,
        end_date=end,
        granularity=granularity,
        parsed=True,
    )


def _fiscal_year_bounds(
    first_year: int,
    second_year: int | None,
    fiscal_year_start_month: int,
) -> tuple[date, date]:
    expanded_first = _expand_short_year(first_year)
    if second_year is None:
        end_year = expanded_first
        start_year = end_year if fiscal_year_start_month == 1 else end_year - 1
    else:
        expanded_second = _expand_short_year(second_year)
        if second_year < 100:
            century = expanded_first // 100 * 100
            expanded_second = century + second_year
            if expanded_second < expanded_first:
                expanded_second += 100
        start_year = expanded_first
        end_year = expanded_second

    start = date(start_year, fiscal_year_start_month, 1)
    end_month = 12 if fiscal_year_start_month == 1 else fiscal_year_start_month - 1
    boundary_year = end_year if fiscal_year_start_month != 1 else start_year
    return start, _month_end(boundary_year, end_month)


def parse_date_range(
    temporal_scope: str,
    *,
    fiscal_year_start_month: int = 4,
) -> NormalizedTemporalScope:
    """Parse common reporting periods into inclusive deterministic boundaries."""

    if not 1 <= fiscal_year_start_month <= 12:
        raise ValueError("fiscal_year_start_month must be between 1 and 12")

    raw = temporal_scope
    text = unicodedata.normalize("NFKC", temporal_scope).strip()
    lowered = text.casefold().replace("–", "-").replace("—", "-")
    dates = _dates_in_text(text)

    if len(dates) >= 2 and re.search(r"\b(?:to|through|until)\b|\s-\s", lowered):
        return _temporal_result(raw, dates[0][1], dates[1][1], TemporalGranularity.DATE_RANGE)

    if dates:
        end_date = dates[0][1]
        duration_match = re.search(
            r"\b(?P<count>three|six|nine|twelve|\d+)\s+months?\s+(?:period\s+)?ended\b",
            lowered,
        )
        duration_words = {"three": 3, "six": 6, "nine": 9, "twelve": 12}
        if duration_match:
            count_text = duration_match.group("count")
            months = duration_words.get(count_text, int(count_text) if count_text.isdigit() else 0)
            start_date = _period_start_for_months(end_date, months)
            if months == 3:
                granularity = TemporalGranularity.QUARTER
            elif months == 12:
                granularity = TemporalGranularity.YEAR
            else:
                granularity = TemporalGranularity.MULTI_MONTH
            return _temporal_result(raw, start_date, end_date, granularity)
        if re.search(r"\b(?:year|fiscal year|financial year)\s+ended\b", lowered):
            start_date = _period_start_for_months(end_date, 12)
            return _temporal_result(raw, start_date, end_date, TemporalGranularity.YEAR)
        if re.search(r"\b(?:quarter|three months)\s+ended\b", lowered):
            start_date = _period_start_for_months(end_date, 3)
            return _temporal_result(raw, start_date, end_date, TemporalGranularity.QUARTER)
        if re.search(r"\b(?:as of|as at|on)\b", lowered):
            return _temporal_result(
                raw,
                end_date,
                end_date,
                TemporalGranularity.POINT_IN_TIME,
            )

    fiscal_match = re.search(
        r"\b(?:fy|fiscal(?:\s+year)?|financial(?:\s+year)?)\s*"
        r"(?P<first>\d{2,4})(?:\s*[-/]\s*(?P<second>\d{2,4}))?\b",
        lowered,
    )
    if fiscal_match:
        first_year = int(fiscal_match.group("first"))
        second_text = fiscal_match.group("second")
        start, end = _fiscal_year_bounds(
            first_year,
            int(second_text) if second_text else None,
            fiscal_year_start_month,
        )
        quarter_match = re.search(r"\bq([1-4])\b", lowered)
        if quarter_match:
            quarter = int(quarter_match.group(1))
            quarter_start = _shift_months(start, (quarter - 1) * 3)
            quarter_end = _shift_months(quarter_start, 3) - timedelta(days=1)
            return _temporal_result(
                raw,
                quarter_start,
                quarter_end,
                TemporalGranularity.QUARTER,
            )
        return _temporal_result(raw, start, end, TemporalGranularity.FISCAL_YEAR)

    month_match = re.fullmatch(
        rf"\s*(?P<month>{_MONTH_PATTERN})\s+(?P<year>\d{{4}})\s*", text, re.I
    )
    if month_match:
        month = _MONTHS[month_match.group("month").casefold()]
        year = int(month_match.group("year"))
        return _temporal_result(
            raw,
            date(year, month, 1),
            _month_end(year, month),
            TemporalGranularity.MONTH,
        )

    year_match = re.fullmatch(r"\s*(?:calendar\s+year\s+)?(?P<year>\d{4})\s*", lowered)
    if year_match:
        year = int(year_match.group("year"))
        return _temporal_result(
            raw,
            date(year, 1, 1),
            date(year, 12, 31),
            TemporalGranularity.YEAR,
        )

    return NormalizedTemporalScope(
        original_text=raw,
        granularity=TemporalGranularity.UNKNOWN,
        parsed=False,
    )


def normalize_fact(
    fact: NormalizableFact,
    *,
    entity_aliases: Mapping[str, str] | None = None,
    predicate_aliases: Mapping[str, str] | None = None,
    target_currency: str | None = None,
    exchange_rates: ExchangeRateTable | None = None,
    fiscal_year_start_month: int = 4,
) -> NormalizedFact:
    """Normalize a fact using only explicit configuration and pure functions."""

    raw_temporal_scope = fact.temporal_scope
    if raw_temporal_scope is None:
        normalized_temporal_scope = None
    elif isinstance(raw_temporal_scope, str):
        normalized_temporal_scope = parse_date_range(
            raw_temporal_scope,
            fiscal_year_start_month=fiscal_year_start_month,
        )
    else:
        temporal_text = getattr(raw_temporal_scope, "raw_text", None)
        normalized_temporal_scope = (
            parse_date_range(temporal_text, fiscal_year_start_month=fiscal_year_start_month)
            if temporal_text
            else None
        )

    raw_data_vintage = getattr(fact, "data_vintage", None)
    if raw_data_vintage is None:
        normalized_data_vintage = None
    elif isinstance(raw_data_vintage, str):
        normalized_data_vintage = parse_date_range(
            raw_data_vintage,
            fiscal_year_start_month=fiscal_year_start_month,
        )
    else:
        vintage_text = getattr(raw_data_vintage, "raw_text", None)
        normalized_data_vintage = (
            parse_date_range(vintage_text, fiscal_year_start_month=fiscal_year_start_month)
            if vintage_text
            else None
        )

    return NormalizedFact(
        fact_id=getattr(fact, "id", None),
        document_id=getattr(fact, "document_id", None),
        entity=normalize_entity_name(fact.subject, entity_aliases),
        original_predicate=fact.predicate,
        canonical_predicate=canonicalize_predicate(fact.predicate, predicate_aliases),
        value=normalize_value(
            fact.value,
            unit=fact.unit,
            currency=fact.currency,
            target_currency=target_currency,
            exchange_rates=exchange_rates,
        ),
        temporal_scope=normalized_temporal_scope,
        scope=getattr(fact, "scope", None),
        data_vintage=normalized_data_vintage,
    )
