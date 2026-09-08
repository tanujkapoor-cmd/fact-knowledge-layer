"""Background document-processing pipeline orchestrating existing adapters."""

from collections.abc import Callable, Sequence
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from backend.config import Settings
from backend.db.repository import KnowledgeRepository
from backend.extraction import (
    EvidenceVerifier,
    ExtractedFactRecord,
    ExtractionCheckpoint,
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
    find_ambiguous_entity_candidates,
    load_alias_config,
    normalize_fact,
)

StatusRegistry = dict[str, dict[str, object]]
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
        self._alias_config = load_alias_config(settings.alias_config_path)

    def _default_adapter(self) -> FactExtractionAdapter:
        if self._settings.llm_provider == "gemini":
            api_key = self._settings.gemini_api_key
            return GeminiStructuredFactAdapter(
                model=self._settings.llm_model,
                api_key=api_key.get_secret_value() if api_key else None,
                max_attempts=self._settings.llm_max_attempts,
                retry_base_seconds=self._settings.llm_retry_base_seconds,
            )
        api_key = self._settings.openai_api_key
        return OpenAIStructuredFactAdapter(
            model=self._settings.llm_model,
            api_key=api_key.get_secret_value() if api_key else None,
            max_attempts=self._settings.llm_max_attempts,
            retry_base_seconds=self._settings.llm_retry_base_seconds,
        )

    def _checkpoint(
        self,
        document_id: UUID,
        checkpoint: ExtractionCheckpoint,
        records: Sequence[ExtractedFactRecord],
        adapter: FactExtractionAdapter,
    ) -> None:
        with self._session_factory.begin() as session:
            repository = KnowledgeRepository(session)
            for record in records:
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
                        scope=record.candidate.scope,
                        data_vintage=record.candidate.data_vintage,
                    )
                    normalized = normalize_fact(
                        source,
                        entity_aliases=self._alias_config.entity_aliases,
                        predicate_aliases=self._alias_config.predicate_aliases,
                        fiscal_year_start_month=self._settings.fiscal_year_start_month,
                    )
                repository.save_fact(document_id, record, normalized)
            repository.set_document_checkpoint(
                document_id,
                completed_pages=checkpoint.completed_pages,
                completed_batches=checkpoint.completed_batches,
                provider_attempts=checkpoint.provider_attempts,
                model=adapter.model,
                prompt_version=adapter.prompt_version,
            )
        current = self._status_registry.get(str(document_id), {})
        self._status_registry[str(document_id)] = {
            **current,
            "processed_page_count": checkpoint.completed_pages,
            "extraction_batch_count": checkpoint.completed_batches,
            "provider_attempt_count": checkpoint.provider_attempts,
        }

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
                document = repository.get_document(document_id)
                if document is None:
                    raise LookupError(f"document {document_id} does not exist")
                resume_page = document.processed_page_count
                resume_batches = document.extraction_batch_count
                resume_attempts = document.provider_attempt_count
            self._status_registry[str(document_id)] = {
                "status": DocumentStatus.EXTRACTING.value,
                "failure_reason": None,
            }

            adapter = self._adapter_factory()
            FactExtractionService(
                adapter,
                EvidenceVerifier(fuzzy_threshold=self._settings.evidence_fuzzy_threshold),
                batch_character_limit=self._settings.extraction_batch_char_limit,
                batch_page_limit=self._settings.extraction_batch_page_limit,
                start_page=resume_page,
                initial_completed_batches=resume_batches,
                initial_provider_attempts=resume_attempts,
                on_checkpoint=lambda checkpoint, records: self._checkpoint(
                    document_id,
                    checkpoint,
                    records,
                    adapter,
                ),
            ).extract_document(parsed)
            self._set_status(document_id, DocumentStatus.VERIFYING)

            with self._session_factory.begin() as session:
                KnowledgeRepository(session).set_document_status(
                    document_id,
                    DocumentStatus.NORMALIZING,
                )

            self._set_status(document_id, DocumentStatus.CLASSIFYING)
            with self._session_factory.begin() as session:
                facts = KnowledgeRepository(session).eligible_normalized_facts()

            resolved_pair_ids: set[str] = set()
            similarities: dict[str, float] = {}
            if self._settings.ambiguous_entity_matching_enabled:
                ambiguous = find_ambiguous_entity_candidates(
                    facts,
                    lower_similarity=self._settings.ambiguous_entity_lower_similarity,
                    upper_similarity=self._settings.ambiguous_entity_upper_similarity,
                    max_pairs=self._settings.ambiguous_entity_max_pairs,
                )
                resolver = getattr(adapter, "resolve_entity_matches", None)
                if ambiguous and resolver:
                    allowed_ids = {candidate.pair_id for candidate in ambiguous}
                    decisions = resolver(ambiguous).decisions
                    resolved_pair_ids = {
                        decision.pair_id
                        for decision in decisions
                        if decision.same_entity and decision.pair_id in allowed_ids
                    }
                    similarities = {
                        candidate.pair_id: candidate.similarity
                        for candidate in ambiguous
                        if candidate.pair_id in resolved_pair_ids
                    }

            with self._session_factory.begin() as session:
                repository = KnowledgeRepository(session)
                for candidate in block_relationship_candidates(
                    facts,
                    resolved_entity_pair_ids=resolved_pair_ids,
                    entity_similarities=similarities,
                ):
                    if document_id not in {
                        candidate.fact_a.document_id,
                        candidate.fact_b.document_id,
                    }:
                        continue
                    repository.save_relationship(
                        classify_relationship(
                            candidate.fact_a,
                            candidate.fact_b,
                            entity_match_resolved=candidate.entity_match_resolved,
                        )
                    )
                repository.set_document_status(document_id, DocumentStatus.COMPLETED)
            self._status_registry[str(document_id)] = {
                "status": DocumentStatus.COMPLETED.value,
                "failure_reason": None,
            }
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            self._set_status(document_id, DocumentStatus.FAILED, reason)
