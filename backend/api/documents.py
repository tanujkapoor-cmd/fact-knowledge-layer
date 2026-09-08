"""Document upload, processing status, and evidence-grounded fact endpoints."""

from hashlib import sha256
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.dependencies import get_session
from backend.api.presenters import present_document, present_fact
from backend.db.repository import KnowledgeRepository
from backend.extraction.prompt import PROMPT_VERSION
from backend.ingestion.pipeline import DocumentProcessingService
from backend.models.api import (
    DocumentStatusResponse,
    DocumentUploadResponse,
    FactResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile,
    session: SessionDependency,
    retry_failed: bool = False,
) -> DocumentUploadResponse:
    """Queue a PDF once; matching SHA-256 uploads reuse their existing work."""

    file_name = Path(file.filename or "uploaded.pdf").name
    if not file_name.casefold().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF uploads are supported")

    max_bytes = request.app.state.settings.max_upload_bytes
    payload = await file.read(max_bytes + 1)
    await file.close()
    if not payload:
        raise HTTPException(status_code=400, detail="The uploaded PDF is empty")
    if len(payload) > max_bytes:
        raise HTTPException(status_code=413, detail="The uploaded PDF exceeds the size limit")

    digest = sha256(payload).hexdigest()
    repository = KnowledgeRepository(session)
    existing = repository.find_document_by_hash(digest)
    if existing:
        if retry_failed and existing.status == "failed":
            document = repository.prepare_document_retry(
                existing.id,
                model=request.app.state.settings.llm_model,
                prompt_version=PROMPT_VERSION,
            )
            document.file_name = file_name
            session.commit()
            retry_started = True
        else:
            return DocumentUploadResponse(
                id=existing.id,
                file_name=existing.file_name,
                sha256=existing.sha256,
                status=existing.status,
                duplicate_reused=True,
                retry_started=False,
            )
    else:
        retry_started = False

        try:
            document = repository.create_document(file_name, digest)
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = repository.find_document_by_hash(digest)
            if existing is None:
                raise
            return DocumentUploadResponse(
                id=existing.id,
                file_name=existing.file_name,
                sha256=existing.sha256,
                status=existing.status,
                duplicate_reused=True,
                retry_started=False,
            )

    document_id = UUID(document.id)
    request.app.state.processing_status[document.id] = {
        "status": document.status,
        "failure_reason": None,
    }
    processor = DocumentProcessingService(
        request.app.state.db_session_factory,
        request.app.state.settings,
        request.app.state.processing_status,
        adapter_factory=getattr(request.app.state, "extraction_adapter_factory", None),
    )
    background_tasks.add_task(processor.process, document_id, payload, file_name)
    return DocumentUploadResponse(
        id=document_id,
        file_name=file_name,
        sha256=digest,
        status=document.status,
        duplicate_reused=False,
        retry_started=retry_started,
    )


@router.get("/{document_id}", response_model=DocumentStatusResponse)
def get_document_status(
    document_id: UUID,
    session: SessionDependency,
) -> DocumentStatusResponse:
    row = KnowledgeRepository(session).get_document(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return present_document(row)


@router.get("/{document_id}/facts", response_model=list[FactResponse])
def get_document_facts(
    document_id: UUID,
    session: SessionDependency,
) -> list[FactResponse]:
    repository = KnowledgeRepository(session)
    if repository.get_document(document_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return [present_fact(row) for row in repository.list_facts(document_id)]
