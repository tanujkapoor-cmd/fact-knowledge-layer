"""Evidence verification tests, including fabricated-quote rejection."""

import pytest

from backend.extraction import EvidenceMatchMethod, EvidenceVerifier
from backend.models import EvidenceStatus


def test_exact_quote_returns_page_local_offsets() -> None:
    page_text = "Overview\nRevenue increased by 10% in FY2024.\nEnd"
    quote = "Revenue increased by 10% in FY2024."

    result = EvidenceVerifier().verify(page_text, quote)

    assert result.status is EvidenceStatus.VERIFIED
    assert result.method is EvidenceMatchMethod.EXACT
    assert page_text[result.start_offset : result.end_offset] == quote
    assert result.source_quote == quote


def test_whitespace_normalization_recovers_actual_source_substring() -> None:
    page_text = "Revenue increased  by 10%\nfor the financial year."
    requested_quote = "Revenue increased by 10% for the financial year."

    result = EvidenceVerifier().verify(page_text, requested_quote)

    assert result.status is EvidenceStatus.VERIFIED
    assert result.method is EvidenceMatchMethod.NORMALIZED
    assert result.source_quote == "Revenue increased  by 10%\nfor the financial year."
    assert page_text[result.start_offset : result.end_offset] == result.source_quote


def test_line_hyphenation_recovers_verbatim_source_substring() -> None:
    page_text = "The company expanded its inter-\nnational delivery network in FY2024."
    requested_quote = "The company expanded its international delivery network in FY2024."

    result = EvidenceVerifier().verify(page_text, requested_quote)

    assert result.status is EvidenceStatus.VERIFIED
    assert result.method is EvidenceMatchMethod.NORMALIZED
    assert "inter-\nnational" in result.source_quote
    assert page_text[result.start_offset : result.end_offset] == result.source_quote


def test_small_transcription_difference_can_be_fuzzy_matched() -> None:
    page_text = "Revenue from contracts increased to INR 10,245 million during FY2024."
    requested_quote = "Revenue from contract increased to INR 10,245 million during FY2024."

    result = EvidenceVerifier(fuzzy_threshold=90).verify(page_text, requested_quote)

    assert result.status is EvidenceStatus.VERIFIED
    assert result.method is EvidenceMatchMethod.FUZZY
    assert result.similarity_score >= 90
    assert page_text[result.start_offset : result.end_offset] == result.source_quote


def test_fabricated_quote_is_rejected() -> None:
    page_text = "Revenue increased by 10% in FY2024."
    fabricated_quote = "The board approved a dividend of INR 500 crore for FY2024."

    result = EvidenceVerifier().verify(page_text, fabricated_quote)

    assert result.status is EvidenceStatus.FAILED
    assert result.method is EvidenceMatchMethod.NONE
    assert result.start_offset is None
    assert result.end_offset is None
    assert result.source_quote is None
    assert "not found" in result.failure_reason


def test_short_non_exact_quote_is_not_fuzzy_matched() -> None:
    result = EvidenceVerifier().verify("Revenue was 100.", "Reveneu")

    assert result.status is EvidenceStatus.FAILED
    assert "too short" in result.failure_reason


def test_verifier_rejects_invalid_threshold_configuration() -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        EvidenceVerifier(fuzzy_threshold=101)
    with pytest.raises(ValueError, match="positive"):
        EvidenceVerifier(minimum_fuzzy_characters=0)
