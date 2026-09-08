"""Convert database rows to stable HTTP response contracts."""

from backend.db.tables import DocumentRow, FactRow, RelationshipRow
from backend.models import ConfidenceScore, EvidenceReference, EvidenceStatus, FactConfidence
from backend.models.api import (
    DocumentStatusResponse,
    FactResponse,
    RelationshipResponse,
    VerificationDetailsResponse,
)


def present_document(row: DocumentRow) -> DocumentStatusResponse:
    return DocumentStatusResponse.model_validate(
        {
            "id": row.id,
            "file_name": row.file_name,
            "sha256": row.sha256,
            "status": row.status,
            "created_at": row.created_at,
            "page_count": row.page_count,
            "failure_reason": row.failure_reason,
            "processed_page_count": row.processed_page_count,
            "extraction_batch_count": row.extraction_batch_count,
            "provider_attempt_count": row.provider_attempt_count,
            "retry_count": row.retry_count,
            "last_checkpoint_at": row.last_checkpoint_at,
        }
    )


def present_fact(row: FactRow) -> FactResponse:
    return FactResponse.model_validate(
        {
            "id": row.id,
            "document_id": row.document_id,
            "subject": row.subject,
            "predicate": row.predicate,
            "value": row.value,
            "unit": row.unit,
            "currency": row.currency,
            "temporal_scope": row.temporal_scope,
            "scope": row.scope,
            "data_vintage": row.data_vintage,
            "evidence": EvidenceReference(
                physical_page_number=row.physical_page_number,
                printed_page_label=row.printed_page_label,
                quote=row.evidence_quote,
                start_offset=row.evidence_start_offset,
                end_offset=row.evidence_end_offset,
                status=EvidenceStatus(row.evidence_status),
                failure_reason=row.evidence_failure_reason,
            ),
            "verification": VerificationDetailsResponse(
                method=row.verification_method,
                similarity_score=row.verification_similarity,
            ),
            "confidence": FactConfidence(
                extraction=ConfidenceScore.model_validate(row.extraction_confidence),
                evidence_verification=ConfidenceScore.model_validate(row.evidence_confidence),
            ),
            "classification_eligible": row.classification_eligible,
        }
    )


def present_relationship(
    row: RelationshipRow,
    facts_by_id: dict[str, FactRow],
) -> RelationshipResponse:
    return RelationshipResponse.model_validate(
        {
            "id": row.id,
            "classification": row.classification,
            "reconciliation_reasons": row.reconciliation_reasons,
            "classification_confidence": row.classification_confidence,
            "reasoning_trace": row.reasoning_trace,
            "fact_a": present_fact(facts_by_id[row.fact_a_id]),
            "fact_b": present_fact(facts_by_id[row.fact_b_id]),
        }
    )
