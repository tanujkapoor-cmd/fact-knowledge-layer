"""Deterministic checks that a matched quote actually supports selected predicates."""

import re

from backend.extraction.schemas import FactCandidate

_INCORPORATION_PREDICATES = {
    "date of incorporation",
    "incorporation date",
    "incorporated on",
}
_INCORPORATION_CUE = re.compile(
    r"\b(?:incorporat(?:e|ed|es|ing|ion)|found(?:ed|ing)|establish(?:ed|ment)|formed)\b",
    re.IGNORECASE,
)


def classification_exclusion_reason(
    candidate: FactCandidate,
    source_quote: str,
) -> str | None:
    """Return why an aligned claim is unsafe for relationship classification.

    Evidence alignment answers whether the quote exists. This separate guard
    answers whether the quote contains the minimum lexical support required by
    a predicate that models commonly confuse with document metadata.
    """

    predicate_key = " ".join(candidate.predicate.casefold().split())
    if predicate_key in _INCORPORATION_PREDICATES and not _INCORPORATION_CUE.search(source_quote):
        return (
            "the quote contains no incorporation, founding, establishment, or formation "
            "cue; a document or filing date cannot support an incorporation-date claim"
        )
    return None
