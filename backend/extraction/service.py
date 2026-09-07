"""Orchestration of LLM extraction, batching, and evidence verification."""

from collections.abc import Iterator, Sequence

from backend.extraction.adapter import FactExtractionAdapter
from backend.extraction.schemas import (
    EvidenceMatchMethod,
    EvidenceVerification,
    ExtractedFactRecord,
    ExtractionRun,
    FactCandidate,
)
from backend.extraction.verifier import EvidenceVerifier
from backend.ingestion import ParsedPage, ParsedPdf
from backend.models import EvidenceReference, EvidenceStatus
from backend.reasoning.confidence import score_fact_confidence


class FactExtractionService:
    """Extract candidates and enforce evidence grounding before downstream use."""

    def __init__(
        self,
        adapter: FactExtractionAdapter,
        verifier: EvidenceVerifier | None = None,
        *,
        batch_character_limit: int = 50_000,
        batch_page_limit: int = 8,
    ) -> None:
        if batch_character_limit < 1 or batch_page_limit < 1:
            raise ValueError("batch limits must be positive")
        self._adapter = adapter
        self._verifier = verifier or EvidenceVerifier()
        self._batch_character_limit = batch_character_limit
        self._batch_page_limit = batch_page_limit

    def extract_document(self, document: ParsedPdf) -> ExtractionRun:
        """Extract and verify all facts while preserving page boundaries."""

        facts: list[ExtractedFactRecord] = []
        request_ids: list[str] = []

        for pages in self._page_batches(document.pages):
            adapter_result = self._adapter.extract_facts(pages)
            if adapter_result.request_id:
                request_ids.append(adapter_result.request_id)
            facts.extend(self._verify_candidates(adapter_result.candidates, pages))

        return ExtractionRun(
            provider=self._adapter.provider,
            model=self._adapter.model,
            prompt_version=self._adapter.prompt_version,
            request_ids=request_ids,
            facts=facts,
        )

    def _page_batches(self, pages: Sequence[ParsedPage]) -> Iterator[list[ParsedPage]]:
        current_batch: list[ParsedPage] = []
        current_characters = 0

        for page in pages:
            would_exceed_characters = (
                current_batch and current_characters + len(page.text) > self._batch_character_limit
            )
            would_exceed_pages = len(current_batch) >= self._batch_page_limit
            if would_exceed_characters or would_exceed_pages:
                yield current_batch
                current_batch = []
                current_characters = 0

            current_batch.append(page)
            current_characters += len(page.text)

        if current_batch:
            yield current_batch

    def _verify_candidates(
        self,
        candidates: Sequence[FactCandidate],
        pages: Sequence[ParsedPage],
    ) -> list[ExtractedFactRecord]:
        pages_by_number = {page.physical_page_number: page for page in pages}
        records: list[ExtractedFactRecord] = []

        for candidate in candidates:
            page = pages_by_number.get(candidate.page_number)
            if page is None:
                verification = EvidenceVerification(
                    status=EvidenceStatus.FAILED,
                    method=EvidenceMatchMethod.NONE,
                    similarity_score=0.0,
                    requested_quote=candidate.evidence_quote,
                    failure_reason="the model cited a page outside its supplied page batch",
                )
                evidence = EvidenceReference(
                    physical_page_number=candidate.page_number,
                    quote=candidate.evidence_quote,
                    status=EvidenceStatus.FAILED,
                    failure_reason=verification.failure_reason,
                )
            else:
                verification = self._verifier.verify(page.text, candidate.evidence_quote)
                evidence = EvidenceReference(
                    physical_page_number=page.physical_page_number,
                    printed_page_label=page.printed_page_label,
                    quote=verification.source_quote or candidate.evidence_quote,
                    start_offset=verification.start_offset,
                    end_offset=verification.end_offset,
                    status=verification.status,
                    failure_reason=verification.failure_reason,
                )

            records.append(
                ExtractedFactRecord(
                    candidate=candidate,
                    evidence=evidence,
                    verification=verification,
                    confidence=score_fact_confidence(candidate, evidence, verification),
                    classification_eligible=evidence.status is EvidenceStatus.VERIFIED,
                )
            )

        return records
