"""PyMuPDF adapter that converts PDFs into stable page-aware text."""

from hashlib import sha256
from pathlib import Path

import pymupdf

from backend.ingestion.errors import (
    EmptyPdfError,
    InvalidPdfError,
    PasswordProtectedPdfError,
)
from backend.ingestion.labels import detect_visible_page_label
from backend.ingestion.schemas import PAGE_SEPARATOR, PageLabelSource, ParsedPage, ParsedPdf

_PDF_HEADER = b"%PDF-"
_PDF_HEADER_SEARCH_BYTES = 1024


class PdfParser:
    """Parse path- or byte-backed PDFs without document-specific assumptions."""

    def parse_file(self, path: str | Path) -> ParsedPdf:
        """Read and parse a PDF file, retaining its caller-visible name."""

        source_path = Path(path)
        return self.parse_bytes(source_path.read_bytes(), source_name=source_path.name)

    def parse_bytes(self, payload: bytes, source_name: str | None = None) -> ParsedPdf:
        """Parse immutable PDF bytes and return page text with stable offsets."""

        if not payload:
            raise EmptyPdfError("the PDF payload is empty")
        if _PDF_HEADER not in payload[:_PDF_HEADER_SEARCH_BYTES]:
            raise InvalidPdfError("the payload does not contain a PDF header")

        try:
            document = pymupdf.open(stream=payload, filetype="pdf")
        except (pymupdf.FileDataError, RuntimeError) as exc:
            raise InvalidPdfError("PyMuPDF could not open the PDF payload") from exc

        try:
            if document.needs_pass:
                raise PasswordProtectedPdfError("password-protected PDFs are not supported")
            if document.page_count == 0:
                raise EmptyPdfError("the PDF contains no pages")

            explicit_page_labels = bool(document.get_page_labels())
            page_texts = [page.get_text("text", sort=True) for page in document]
            document_text = PAGE_SEPARATOR.join(page_texts)
            parsed_pages: list[ParsedPage] = []
            cursor = 0

            for index, page in enumerate(document):
                if index:
                    cursor += len(PAGE_SEPARATOR)

                page_text = page_texts[index]
                start_offset = cursor
                end_offset = start_offset + len(page_text)
                visible_label = detect_visible_page_label(page)
                metadata_label = page.get_label().strip() if explicit_page_labels else ""

                if visible_label:
                    printed_page_label = visible_label
                    page_label_source = PageLabelSource.VISIBLE_MARGIN
                elif metadata_label:
                    printed_page_label = metadata_label
                    page_label_source = PageLabelSource.PDF_METADATA
                else:
                    printed_page_label = None
                    page_label_source = None

                parsed_pages.append(
                    ParsedPage(
                        physical_page_number=index + 1,
                        printed_page_label=printed_page_label,
                        page_label_source=page_label_source,
                        text=page_text,
                        page_local_end_offset=len(page_text),
                        document_start_offset=start_offset,
                        document_end_offset=end_offset,
                    )
                )
                cursor = end_offset

            return ParsedPdf(
                source_name=source_name,
                sha256=sha256(payload).hexdigest(),
                page_count=document.page_count,
                text=document_text,
                pages=parsed_pages,
            )
        finally:
            document.close()
