"""Relationship exploration endpoint."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.dependencies import get_session
from backend.api.presenters import present_relationship
from backend.db.repository import KnowledgeRepository
from backend.models import RelationshipType
from backend.models.api import RelationshipResponse

router = APIRouter(tags=["relationships"])
SessionDependency = Annotated[Session, Depends(get_session)]
OffsetQuery = Annotated[int, Query(ge=0)]
LimitQuery = Annotated[int, Query(ge=1, le=500)]


@router.get("/relationships", response_model=list[RelationshipResponse])
def get_relationships(
    session: SessionDependency,
    classification: RelationshipType | None = None,
    document_id: UUID | None = None,
    offset: OffsetQuery = 0,
    limit: LimitQuery = 100,
) -> list[RelationshipResponse]:
    repository = KnowledgeRepository(session)
    rows = repository.list_relationships(
        classification=classification.value if classification else None,
        document_id=document_id,
        offset=offset,
        limit=limit,
    )
    facts = repository.get_facts_by_ids(
        [fact_id for row in rows for fact_id in (row.fact_a_id, row.fact_b_id)]
    )
    return [present_relationship(row, facts) for row in rows]
