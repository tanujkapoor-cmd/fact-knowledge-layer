"""Deterministic alignment of LLM evidence quotes to extracted page text."""

from dataclasses import dataclass

from rapidfuzz import fuzz

from backend.extraction.schemas import EvidenceMatchMethod, EvidenceVerification
from backend.models import EvidenceStatus


@dataclass(frozen=True, slots=True)
class _NormalizedText:
    text: str
    source_starts: tuple[int, ...]
    source_ends: tuple[int, ...]

    def recover_source_bounds(self, start: int, end: int) -> tuple[int, int]:
        return self.source_starts[start], self.source_ends[end - 1]


def _hyphenated_line_break_end(text: str, index: int, previous_character: str) -> int | None:
    if text[index] not in {"-", "\u00ad"} or not previous_character.isalnum():
        return None

    cursor = index + 1
    if text[index] == "\u00ad" and cursor < len(text) and text[cursor].isalnum():
        return cursor

    while cursor < len(text) and text[cursor] in {" ", "\t"}:
        cursor += 1
    if cursor >= len(text) or text[cursor] not in {"\r", "\n"}:
        return None

    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor if cursor < len(text) and text[cursor].isalnum() else None


def _normalize_with_mapping(text: str) -> _NormalizedText:
    characters: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    index = 0

    while index < len(text):
        character = text[index]
        previous_character = characters[-1] if characters else ""
        hyphenation_end = _hyphenated_line_break_end(text, index, previous_character)
        if hyphenation_end is not None:
            index = hyphenation_end
            continue

        if character.isspace():
            run_start = index
            while index < len(text) and text[index].isspace():
                index += 1
            if characters and characters[-1] != " " and index < len(text):
                characters.append(" ")
                starts.append(run_start)
                ends.append(index)
            continue

        characters.append(character)
        starts.append(index)
        ends.append(index + 1)
        index += 1

    return _NormalizedText("".join(characters), tuple(starts), tuple(ends))


class EvidenceVerifier:
    """Verify quotes exactly, then normalized, then conservatively fuzzy."""

    def __init__(self, fuzzy_threshold: float = 92.0, minimum_fuzzy_characters: int = 20):
        if not 0 <= fuzzy_threshold <= 100:
            raise ValueError("fuzzy_threshold must be between 0 and 100")
        if minimum_fuzzy_characters < 1:
            raise ValueError("minimum_fuzzy_characters must be positive")
        self._fuzzy_threshold = fuzzy_threshold
        self._minimum_fuzzy_characters = minimum_fuzzy_characters

    def verify(self, page_text: str, requested_quote: str) -> EvidenceVerification:
        """Locate a quote and always return offsets into the original page text."""

        exact_start = page_text.find(requested_quote)
        if exact_start >= 0:
            exact_end = exact_start + len(requested_quote)
            return self._verified(
                requested_quote,
                page_text,
                exact_start,
                exact_end,
                EvidenceMatchMethod.EXACT,
                100.0,
            )

        normalized_page = _normalize_with_mapping(page_text)
        normalized_quote = _normalize_with_mapping(requested_quote).text
        if not normalized_quote:
            return self._failed(requested_quote, "the evidence quote contains no text")

        normalized_start = normalized_page.text.find(normalized_quote)
        if normalized_start >= 0:
            normalized_end = normalized_start + len(normalized_quote)
            source_start, source_end = normalized_page.recover_source_bounds(
                normalized_start, normalized_end
            )
            return self._verified(
                requested_quote,
                page_text,
                source_start,
                source_end,
                EvidenceMatchMethod.NORMALIZED,
                100.0,
            )

        if len(normalized_quote) < self._minimum_fuzzy_characters:
            return self._failed(
                requested_quote,
                "the quote was not found and is too short for safe fuzzy matching",
            )

        alignment = fuzz.partial_ratio_alignment(
            normalized_quote,
            normalized_page.text,
            score_cutoff=self._fuzzy_threshold,
        )
        if alignment is None or alignment.dest_end <= alignment.dest_start:
            return self._failed(requested_quote, "the quote was not found on the stated page")

        matched_length = alignment.dest_end - alignment.dest_start
        minimum_coverage = max(1, int(len(normalized_quote) * 0.75))
        if matched_length < minimum_coverage:
            return self._failed(requested_quote, "the fuzzy match covered too little of the quote")

        source_start, source_end = normalized_page.recover_source_bounds(
            alignment.dest_start, alignment.dest_end
        )
        return self._verified(
            requested_quote,
            page_text,
            source_start,
            source_end,
            EvidenceMatchMethod.FUZZY,
            float(alignment.score),
        )

    @staticmethod
    def _verified(
        requested_quote: str,
        page_text: str,
        start_offset: int,
        end_offset: int,
        method: EvidenceMatchMethod,
        score: float,
    ) -> EvidenceVerification:
        return EvidenceVerification(
            status=EvidenceStatus.VERIFIED,
            method=method,
            similarity_score=score,
            requested_quote=requested_quote,
            source_quote=page_text[start_offset:end_offset],
            start_offset=start_offset,
            end_offset=end_offset,
        )

    @staticmethod
    def _failed(requested_quote: str, reason: str) -> EvidenceVerification:
        return EvidenceVerification(
            status=EvidenceStatus.FAILED,
            method=EvidenceMatchMethod.NONE,
            similarity_score=0.0,
            requested_quote=requested_quote,
            failure_reason=reason,
        )
