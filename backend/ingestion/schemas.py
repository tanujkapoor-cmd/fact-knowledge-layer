"""Validated output contracts for page-aware PDF parsing."""

from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

PAGE_SEPARATOR = "\f"


class IngestionModel(BaseModel):
    """Strict model that deliberately preserves all extracted whitespace."""

    model_config = ConfigDict(extra="forbid")


class PageLabelSource(StrEnum):
    VISIBLE_MARGIN = "visible_margin"
    PDF_METADATA = "pdf_metadata"


class ParsedPage(IngestionModel):
    """Text and stable offsets for one physical PDF page."""

    physical_page_number: int = Field(ge=1)
    printed_page_label: str | None = None
    page_label_source: PageLabelSource | None = None
    text: str
    page_local_start_offset: int = Field(default=0, ge=0)
    page_local_end_offset: int = Field(ge=0)
    document_start_offset: int = Field(ge=0)
    document_end_offset: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_offsets(self) -> Self:
        if self.page_local_start_offset != 0:
            raise ValueError("page-local text must start at offset zero")
        if self.page_local_end_offset != len(self.text):
            raise ValueError("page_local_end_offset must equal the page text length")
        if self.document_end_offset - self.document_start_offset != len(self.text):
            raise ValueError("document offsets must span the exact page text")
        if (self.printed_page_label is None) != (self.page_label_source is None):
            raise ValueError("a page label and its source must be provided together")
        return self

    def source_slice(self, start_offset: int, end_offset: int) -> str:
        """Return a page-local source substring with strict bounds checking."""

        if start_offset < 0 or end_offset <= start_offset:
            raise ValueError("source offsets must satisfy 0 <= start < end")
        if end_offset > self.page_local_end_offset:
            raise ValueError("source offsets exceed the page text length")
        return self.text[start_offset:end_offset]


class ParsedPdf(IngestionModel):
    """Complete parse result for one immutable PDF payload."""

    source_name: str | None = None
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    page_count: int = Field(ge=1)
    text: str
    pages: list[ParsedPage] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_document_layout(self) -> Self:
        if self.page_count != len(self.pages):
            raise ValueError("page_count must equal the number of parsed pages")

        expected_text = PAGE_SEPARATOR.join(page.text for page in self.pages)
        if self.text != expected_text:
            raise ValueError("document text must be the page text joined by form feeds")

        expected_start = 0
        for index, page in enumerate(self.pages):
            if page.physical_page_number != index + 1:
                raise ValueError("physical page numbers must be consecutive and one-based")
            if page.document_start_offset != expected_start:
                raise ValueError("page document offsets must be consecutive")
            if self.text[page.document_start_offset : page.document_end_offset] != page.text:
                raise ValueError("page document offsets do not recover the exact page text")
            expected_start = page.document_end_offset + len(PAGE_SEPARATOR)
        return self

    @property
    def file_name(self) -> str | None:
        """Return only the final path component supplied by the caller."""

        return Path(self.source_name).name if self.source_name else None
