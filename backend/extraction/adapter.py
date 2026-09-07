"""Provider-neutral contract for structured fact extraction."""

from collections.abc import Sequence
from typing import Protocol

from backend.extraction.schemas import AdapterExtractionResult
from backend.ingestion import ParsedPage


class FactExtractionAdapter(Protocol):
    """Small boundary that isolates all LLM provider calls."""

    @property
    def provider(self) -> str: ...

    @property
    def model(self) -> str: ...

    @property
    def prompt_version(self) -> str: ...

    def extract_facts(self, pages: Sequence[ParsedPage]) -> AdapterExtractionResult:
        """Return schema-validated candidate facts for the supplied pages."""

        ...
