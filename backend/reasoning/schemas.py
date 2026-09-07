"""Validated data contracts produced by deterministic normalization."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from backend.models import ReasoningStep, RelationshipType

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ReasoningModel(BaseModel):
    """Strict, immutable value object used by deterministic reasoning."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ValueKind(StrEnum):
    NUMERIC = "numeric"
    TEXT = "text"


class TemporalGranularity(StrEnum):
    POINT_IN_TIME = "point_in_time"
    MONTH = "month"
    QUARTER = "quarter"
    MULTI_MONTH = "multi_month"
    YEAR = "year"
    FISCAL_YEAR = "fiscal_year"
    DATE_RANGE = "date_range"
    UNKNOWN = "unknown"


class ReconciliationReason(StrEnum):
    """Context that deterministically explains an apparent value difference."""

    TIME_PERIOD = "time_period"
    UNIT = "unit"
    CURRENCY = "currency"
    SCOPE = "scope"


class EntityNormalization(ReasoningModel):
    """Canonical entity representation with an auditable transformation trace."""

    original_name: NonEmptyText
    canonical_name: NonEmptyText
    comparison_key: NonEmptyText
    alias_applied: bool = False
    removed_suffixes: tuple[str, ...] = ()


class ExchangeRateTable(ReasoningModel):
    """Dated rates where one source unit multiplied by its rate equals the base."""

    base_currency: str = Field(min_length=3, max_length=3)
    as_of_date: date
    rates_to_base: dict[str, Decimal]

    @field_validator("base_currency", mode="before")
    @classmethod
    def uppercase_base_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("rates_to_base", mode="before")
    @classmethod
    def uppercase_rate_currencies(cls, value: dict[str, Decimal]) -> dict[str, Decimal]:
        return {key.strip().upper(): Decimal(str(rate)) for key, rate in value.items()}

    @model_validator(mode="after")
    def validate_rates(self) -> Self:
        if self.rates_to_base.get(self.base_currency) != Decimal("1"):
            raise ValueError("the base currency must have a rate of 1")
        if any(rate <= 0 for rate in self.rates_to_base.values()):
            raise ValueError("exchange rates must be positive")
        return self


class NormalizedValue(ReasoningModel):
    """Numeric or textual value with each deterministic conversion exposed."""

    kind: ValueKind
    original_value: str
    original_numeric_value: Decimal | None = None
    normalized_numeric_value: Decimal | None = None
    normalized_text: str | None = None
    original_unit: str | None = None
    canonical_unit: str | None = None
    unit_dimension: str | None = None
    scale_factor: Decimal = Decimal("1")
    unit_conversion_factor: Decimal = Decimal("1")
    original_currency: str | None = None
    canonical_currency: str | None = None
    currency_conversion_rate: Decimal | None = None
    exchange_rate_date: date | None = None

    @model_validator(mode="after")
    def validate_value_kind(self) -> Self:
        if self.kind is ValueKind.NUMERIC:
            if self.original_numeric_value is None or self.normalized_numeric_value is None:
                raise ValueError("numeric values require original and normalized numbers")
            if self.normalized_text is not None:
                raise ValueError("numeric values cannot also contain normalized text")
        elif not self.normalized_text:
            raise ValueError("text values require normalized text")
        return self


class NormalizedTemporalScope(ReasoningModel):
    """Parsed temporal boundaries while retaining the exact supplied wording."""

    original_text: str
    start_date: date | None = None
    end_date: date | None = None
    granularity: TemporalGranularity
    parsed: bool

    @model_validator(mode="after")
    def validate_temporal_state(self) -> Self:
        if self.parsed and (self.start_date is None or self.end_date is None):
            raise ValueError("parsed temporal scopes require both date boundaries")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("temporal start_date must not follow end_date")
        return self


class NormalizedFact(ReasoningModel):
    """A fact transformed into deterministic comparison fields."""

    fact_id: UUID | None = None
    document_id: UUID | None = None
    entity: EntityNormalization
    original_predicate: NonEmptyText
    canonical_predicate: NonEmptyText
    value: NormalizedValue
    temporal_scope: NormalizedTemporalScope | None = None
    scope: str | None = None


class RelationshipCandidate(ReasoningModel):
    """A cross-document pair emitted by deterministic candidate blocking."""

    fact_a: NormalizedFact
    fact_b: NormalizedFact


class ClassificationDecision(ReasoningModel):
    """Deterministic classifier output before persistence and confidence scoring."""

    fact_a_id: UUID | None = None
    fact_b_id: UUID | None = None
    classification: RelationshipType
    reconciliation_reasons: tuple[ReconciliationReason, ...] = ()
    reasoning_trace: tuple[ReasoningStep, ...] = Field(min_length=1)
