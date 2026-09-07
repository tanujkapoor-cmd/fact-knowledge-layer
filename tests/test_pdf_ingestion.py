"""Tests for page-aware, general-purpose PDF ingestion."""

from hashlib import sha256

import pymupdf
import pytest

from backend.ingestion import (
    EmptyPdfError,
    InvalidPdfError,
    PageLabelSource,
    PasswordProtectedPdfError,
    PdfParser,
)
from backend.ingestion.schemas import PAGE_SEPARATOR


def _make_pdf(
    page_bodies: list[str],
    *,
    visible_labels: list[str | None] | None = None,
    metadata_labels: list[dict[str, int | str]] | None = None,
) -> bytes:
    document = pymupdf.open()
    labels = visible_labels or [None] * len(page_bodies)

    for body, label in zip(page_bodies, labels, strict=True):
        page = document.new_page()
        page.insert_text((72, 72), body)
        if label:
            page.insert_text((page.rect.width / 2, page.rect.height - 24), label)

    if metadata_labels:
        document.set_page_labels(metadata_labels)

    payload = document.tobytes()
    document.close()
    return payload


def test_parser_preserves_pages_hash_and_exact_offsets() -> None:
    payload = _make_pdf(
        ["Revenue was INR 100 crore.", "Revenue was INR 120 crore."],
        visible_labels=["127", "131"],
    )

    parsed = PdfParser().parse_bytes(payload, source_name="financial-report.pdf")

    assert parsed.page_count == 2
    assert parsed.sha256 == sha256(payload).hexdigest()
    assert parsed.file_name == "financial-report.pdf"
    assert parsed.text == PAGE_SEPARATOR.join(page.text for page in parsed.pages)

    first_page, second_page = parsed.pages
    assert first_page.physical_page_number == 1
    assert second_page.physical_page_number == 2
    assert first_page.printed_page_label == "127"
    assert first_page.page_label_source is PageLabelSource.VISIBLE_MARGIN
    assert second_page.printed_page_label == "131"
    assert second_page.document_start_offset == first_page.document_end_offset + 1

    quote = "INR 100 crore"
    start_offset = first_page.text.index(quote)
    end_offset = start_offset + len(quote)
    assert first_page.source_slice(start_offset, end_offset) == quote
    assert (
        parsed.text[first_page.document_start_offset : first_page.document_end_offset]
        == first_page.text
    )


def test_parser_uses_explicit_pdf_label_when_no_visible_label_exists() -> None:
    payload = _make_pdf(
        ["A page without a visible footer."],
        metadata_labels=[{"startpage": 0, "prefix": "A-", "style": "D", "firstpagenum": 10}],
    )

    parsed = PdfParser().parse_bytes(payload)

    assert parsed.pages[0].printed_page_label == "A-10"
    assert parsed.pages[0].page_label_source is PageLabelSource.PDF_METADATA


def test_parser_combines_two_page_spread_labels() -> None:
    document = pymupdf.open()
    page = document.new_page(width=1200, height=840)
    page.insert_text((72, 72), "Content from a two-page report spread.")
    page.insert_text((50, 815), "100")
    page.insert_text((72, 815), "Example Limited")
    page.insert_text((1040, 815), "Annual Report 2023-24")
    page.insert_text((1130, 815), "101")
    payload = document.tobytes()
    document.close()

    parsed = PdfParser().parse_bytes(payload)

    assert parsed.pages[0].printed_page_label == "100–101"
    assert parsed.pages[0].page_label_source is PageLabelSource.VISIBLE_MARGIN


def test_parser_does_not_treat_body_numbers_as_page_labels() -> None:
    payload = _make_pdf(["The company delivered 2024 parcels and earned INR 100."])

    parsed = PdfParser().parse_bytes(payload)

    assert parsed.pages[0].printed_page_label is None
    assert parsed.pages[0].page_label_source is None


def test_file_and_byte_entry_points_return_the_same_content(tmp_path) -> None:
    payload = _make_pdf(["A reusable parser must not depend on a file name."])
    pdf_path = tmp_path / "unseen-document.pdf"
    pdf_path.write_bytes(payload)

    from_file = PdfParser().parse_file(pdf_path)
    from_bytes = PdfParser().parse_bytes(payload, source_name=pdf_path.name)

    assert from_file == from_bytes


def test_parser_rejects_non_pdf_bytes() -> None:
    with pytest.raises(InvalidPdfError, match="PDF header"):
        PdfParser().parse_bytes(b"This is not a PDF")


def test_parser_rejects_empty_and_corrupt_pdf_payloads() -> None:
    with pytest.raises(EmptyPdfError, match="empty"):
        PdfParser().parse_bytes(b"")

    with pytest.raises(InvalidPdfError, match="could not open"):
        PdfParser().parse_bytes(b"%PDF-1.7\nThis payload is corrupt")


def test_page_source_slice_rejects_invalid_bounds() -> None:
    parsed = PdfParser().parse_bytes(_make_pdf(["Offset-safe text"]))
    page = parsed.pages[0]

    with pytest.raises(ValueError, match="0 <= start < end"):
        page.source_slice(4, 4)
    with pytest.raises(ValueError, match="exceed"):
        page.source_slice(0, len(page.text) + 1)


def test_parser_rejects_password_protected_pdf() -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Confidential facts")
    payload = document.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner-password",
        user_pw="user-password",
    )
    document.close()

    with pytest.raises(PasswordProtectedPdfError):
        PdfParser().parse_bytes(payload)
