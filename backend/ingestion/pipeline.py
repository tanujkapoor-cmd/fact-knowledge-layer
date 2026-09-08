"""Background document-processing pipeline orchestrating existing adapters."""

from collections.abc import Callable
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from backend.config import Settings
from backend.db.repository import KnowledgeRepository
from backend.extraction import (
    EvidenceVerifier,
    FactExtractionAdapter,
    FactExtractionService,
    GeminiStructuredFactAdapter,
)
from backend.extraction.openai_adapter import OpenAIStructuredFactAdapter
from backend.ingestion.parser import PdfParser
from backend.models import DocumentStatus
from backend.reasoning import (
    block_relationship_candidates,
    classify_relationship,
    normalize_fact,
)

StatusRegistry = dict[str, dict[str, str | None]]
AdapterFactory = Callable[[], FactExtractionAdapter]


class DocumentProcessingService:
    """Process one immutable upload with a fresh session per state transition."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        settings: Settings,
        status_registry: StatusRegistry,
        *,
        adapter_factory: AdapterFactory | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._status_registry = status_registry
        self._adapter_factory = adapter_factory or self._default_adapter

    def _default_adapter(self) -> FactExtractionAdapter:
        if self._settings.llm_provider == "gemini":
            api_key = self._settings.gemini_api_key
            return GeminiStructuredFactAdapter(
                model=self._settings.llm_model,
                api_key=api_key.get_secret_value() if api_key else None,
            )
        api_key = self._settings.openai_api_key
        return OpenAIStructuredFactAdapter(
            model=self._settings.llm_model,
            api_key=api_key.get_secret_value() if api_key else None,
        )

    def _set_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        failure_reason: str | None = None,
    ) -> None:
        with self._session_factory.begin() as session:
            KnowledgeRepository(session).set_document_status(
                document_id,
                status,
                failure_reason=failure_reason,
            )
        self._status_registry[str(document_id)] = {
            "status": status.value,
            "failure_reason": failure_reason,
        }

    def process(self, document_id: UUID, payload: bytes, file_name: str) -> None:
        """Run ingestion through classification; retain an explicit failure state."""

        try:
            self._set_status(document_id, DocumentStatus.INGESTING)
            parsed = PdfParser().parse_bytes(payload, source_name=file_name)
            with self._session_factory.begin() as session:
                repository = KnowledgeRepository(session)
                repository.save_pages(document_id, parsed)
                repository.set_document_status(document_id, DocumentStatus.EXTRACTING)
            self._status_registry[str(document_id)] = {
                "status": DocumentStatus.EXTRACTING.value,
                "failure_reason": None,
            }

            extraction = FactExtractionService(
                self._adapter_factory(),
                EvidenceVerifier(fuzzy_threshold=self._settings.evidence_fuzzy_threshold),
                batch_character_limit=self._settings.extraction_batch_char_limit,
                batch_page_limit=self._settings.extraction_batch_page_limit,
            ).extract_document(parsed)
            self._set_status(document_id, DocumentStatus.VERIFYING)

            with self._session_factory.begin() as session:
                repository = KnowledgeRepository(session)
                repository.set_document_status(document_id, DocumentStatus.NORMALIZING)
                for record in extraction.facts:
                    fact_id = uuid4()
                    normalized = None
                    if record.classification_eligible:
                        source = SimpleNamespace(
                            id=fact_id,
                            document_id=document_id,
                            subject=record.candidate.subject,
                            predicate=record.candidate.predicate,
                            value=record.candidate.value,
                            unit=record.candidate.unit,
                            currency=record.candidate.currency,
                            temporal_scope=record.candidate.temporal_scope,
                            scope=None,
                        )
                        normalized = normalize_fact(
                            source,
                            fiscal_year_start_month=self._settings.fiscal_year_start_month,
                        )
                    repository.save_fact(document_id, record, normalized)

            self._set_status(document_id, DocumentStatus.CLASSIFYING)
            with self._session_factory.begin() as session:
                repository = KnowledgeRepository(session)
                facts = repository.eligible_normalized_facts()
                for candidate in block_relationship_candidates(facts):
                    if document_id not in {
                        candidate.fact_a.document_id,
                        candidate.fact_b.document_id,
                    }:
                        continue
                    repository.save_relationship(
                        classify_relationship(candidate.fact_a, candidate.fact_b)
                    )
                repository.set_document_status(document_id, DocumentStatus.COMPLETED)
            self._status_registry[str(document_id)] = {
                "status": DocumentStatus.COMPLETED.value,
                "failure_reason": None,
            }
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            self._set_status(document_id, DocumentStatus.FAILED, reason)
