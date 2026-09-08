"""Pure deterministic normalization and classification package."""

from backend.reasoning.aliases import AliasConfig, load_alias_config
from backend.reasoning.classify import (
    CLASSIFIER_VERSION,
    block_relationship_candidates,
    classify_relationship,
    find_ambiguous_entity_candidates,
)
from backend.reasoning.confidence import (
    CONFIDENCE_VERSION,
    score_classification,
    score_evidence_verification,
    score_extraction,
    score_fact_confidence,
)
from backend.reasoning.normalize import (
    NORMALIZATION_VERSION,
    CurrencyConversionError,
    canonicalize_predicate,
    normalize_entity_name,
    normalize_fact,
    normalize_value,
    parse_date_range,
)
from backend.reasoning.schemas import (
    AmbiguousEntityCandidate,
    ClassificationDecision,
    EntityNormalization,
    ExchangeRateTable,
    NormalizedFact,
    NormalizedTemporalScope,
    NormalizedValue,
    ReconciliationReason,
    RelationshipCandidate,
    TemporalGranularity,
    ValueKind,
)

__all__ = [
    "AliasConfig",
    "AmbiguousEntityCandidate",
    "CLASSIFIER_VERSION",
    "CONFIDENCE_VERSION",
    "ClassificationDecision",
    "CurrencyConversionError",
    "EntityNormalization",
    "ExchangeRateTable",
    "NormalizedFact",
    "NormalizedTemporalScope",
    "NormalizedValue",
    "NORMALIZATION_VERSION",
    "ReconciliationReason",
    "RelationshipCandidate",
    "TemporalGranularity",
    "ValueKind",
    "block_relationship_candidates",
    "canonicalize_predicate",
    "classify_relationship",
    "find_ambiguous_entity_candidates",
    "load_alias_config",
    "normalize_entity_name",
    "normalize_fact",
    "normalize_value",
    "parse_date_range",
    "score_classification",
    "score_evidence_verification",
    "score_extraction",
    "score_fact_confidence",
]
