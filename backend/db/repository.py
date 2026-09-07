"""Small SQLAlchemy repository with explicit domain-to-row conversions."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from backend.db.tables import DocumentRow, FactRow, PageRow, RelationshipRow
from backend.extraction import ExtractedFactRecord
from backend.ingestion import ParsedPdf
from backend.models import DocumentStatus
from backend.reasoning import ClassificationDecision, NormalizedFact
from backend.reasoning.confidence import score_classification


class KnowledgeRepository:
    """Persistence operations used by the HTTP and processing layers."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def find_document_by_hash(self, sha256: str) -> DocumentRow | None:
        return self.session.scalar(select(DocumentRow).where(DocumentRow.sha256 == sha256))

    def get_document(self, document_id: UUID | str) -> DocumentRow | None:
        return self.session.get(DocumentRow, str(document_id))

    def create_document(self, file_name: str, sha256: str) -> DocumentRow:
        row = DocumentRow(
            id=str(uuid4()),
            file_name=file_name,
            sha256=sha256,
            status=DocumentStatus.QUEUED.value,
            created_at=datetime.now(UTC),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def set_document_status(
        self,
        document_id: UUID | str,
        status: DocumentStatus,
        *,
        failure_reason: str | None = None,
    ) -> None:
        document = self.get_document(document_id)
        if document is None:
            raise LookupError(f"document {document_id} does not exist")
        document.status = status.value
        document.failure_reason = failure_reason

    def save_pages(self, document_id: UUID | str, parsed: ParsedPdf) -> None:
        document = self.get_document(document_id)
        if document is None:
            raise LookupError(f"document {document_id} does not exist")
        document.page_count = parsed.page_count
        self.session.add_all(
            [
                PageRow(
                    document_id=str(document_id),
                    physical_page_number=page.physical_page_number,
                    printed_page_label=page.printed_page_label,
                    page_label_source=page.page_label_source.value
                    if page.page_label_source
                    else None,
                    text=page.text,
                    document_start_offset=page.document_start_offset,
                    document_end_offset=page.document_end_offset,
                )
                for page in parsed.pages
            ]
        )

    def save_fact(
        self,
        document_id: UUID | str,
        record: ExtractedFactRecord,
        normalized: NormalizedFact | None,
    ) -> FactRow:
        candidate = record.candidate
        evidence = record.evidence
        row = FactRow(
            id=str(normalized.fact_id if normalized and normalized.fact_id else uuid4()),
            document_id=str(document_id),
            subject=candidate.subject,
            predicate=candidate.predicate,
            value=candidate.value,
            unit=candidate.unit,
            currency=candidate.currency,
            temporal_scope=candidate.temporal_scope,
            physical_page_number=evidence.physical_page_number,
            printed_page_label=evidence.printed_page_label,
            evidence_quote=evidence.quote,
            evidence_start_offset=evidence.start_offset,
            evidence_end_offset=evidence.end_offset,
            evidence_status=evidence.status.value,
            evidence_failure_reason=evidence.failure_reason,
            verification_method=record.verification.method.value,
            verification_similarity=record.verification.similarity_score,
            classification_eligible=record.classification_eligible,
            extraction_confidence=record.confidence.extraction.model_dump(mode="json"),
            evidence_confidence=record.confidence.evidence_verification.model_dump(mode="json"),
            normalized_payload=normalized.model_dump(mode="json") if normalized else None,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def eligible_normalized_facts(self) -> list[NormalizedFact]:
        rows = self.session.scalars(
            select(FactRow).where(
                FactRow.classification_eligible.is_(True),
                FactRow.normalized_payload.is_not(None),
            )
        )
        return [NormalizedFact.model_validate(row.normalized_payload) for row in rows]

    def save_relationship(self, decision: ClassificationDecision) -> RelationshipRow:
        if decision.fact_a_id is None or decision.fact_b_id is None:
            raise ValueError("persisted relationships require fact identifiers")
        fact_a_id, fact_b_id = sorted((str(decision.fact_a_id), str(decision.fact_b_id)))
        existing = self.session.scalar(
            select(RelationshipRow).where(
                RelationshipRow.fact_a_id == fact_a_id,
                RelationshipRow.fact_b_id == fact_b_id,
            )
        )
        confidence = score_classification(decision).classification.model_dump(mode="json")
        values = {
            "classification": decision.classification.value,
            "reconciliation_reasons": [reason.value for reason in decision.reconciliation_reasons],
            "classification_confidence": confidence,
            "reasoning_trace": [step.model_dump(mode="json") for step in decision.reasoning_trace],
        }
        if existing:
            for name, value in values.items():
                setattr(existing, name, value)
            return existing

        row = RelationshipRow(
            id=str(uuid4()),
            fact_a_id=fact_a_id,
            fact_b_id=fact_b_id,
            **values,
        )
        self.session.add(row)
        return row

    def list_facts(self, document_id: UUID | str) -> list[FactRow]:
        return list(
            self.session.scalars(
                select(FactRow)
                .where(FactRow.document_id == str(document_id))
                .order_by(FactRow.physical_page_number, FactRow.id)
            )
        )

    def get_facts_by_ids(self, fact_ids: Sequence[str]) -> dict[str, FactRow]:
        return {
            row.id: row
            for row in self.session.scalars(select(FactRow).where(FactRow.id.in_(fact_ids)))
        }

    def list_relationships(
        self,
        *,
        classification: str | None = None,
        document_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[RelationshipRow]:
        statement: Select[tuple[RelationshipRow]] = select(RelationshipRow)
        if classification:
            statement = statement.where(RelationshipRow.classification == classification)
        if document_id:
            fact_ids = select(FactRow.id).where(FactRow.document_id == str(document_id))
            statement = statement.where(
                or_(
                    RelationshipRow.fact_a_id.in_(fact_ids),
                    RelationshipRow.fact_b_id.in_(fact_ids),
                )
            )
        statement = statement.order_by(RelationshipRow.id).offset(offset).limit(limit)
        return list(self.session.scalars(statement))
