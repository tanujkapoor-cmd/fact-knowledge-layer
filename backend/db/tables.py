"""Relational persistence tables for documents, evidence-grounded facts, and decisions."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class DocumentRow(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    file_name: Mapped[str] = mapped_column(String(512))
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer)
    processed_page_count: Mapped[int] = mapped_column(Integer, default=0)
    extraction_batch_count: Mapped[int] = mapped_column(Integer, default=0)
    provider_attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_checkpoint_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checkpoint_model: Mapped[str | None] = mapped_column(String(128))
    checkpoint_prompt_version: Mapped[str | None] = mapped_column(String(64))

    pages: Mapped[list["PageRow"]] = relationship(cascade="all, delete-orphan")
    facts: Mapped[list["FactRow"]] = relationship(cascade="all, delete-orphan")


class PageRow(Base):
    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("document_id", "physical_page_number"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    physical_page_number: Mapped[int] = mapped_column(Integer)
    printed_page_label: Mapped[str | None] = mapped_column(String(64))
    page_label_source: Mapped[str | None] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)
    document_start_offset: Mapped[int] = mapped_column(Integer)
    document_end_offset: Mapped[int] = mapped_column(Integer)


class FactRow(Base):
    __tablename__ = "facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    subject: Mapped[str] = mapped_column(Text)
    predicate: Mapped[str] = mapped_column(Text)
    value: Mapped[str] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(128))
    currency: Mapped[str | None] = mapped_column(String(16))
    temporal_scope: Mapped[str | None] = mapped_column(Text)
    scope: Mapped[str | None] = mapped_column(Text)
    data_vintage: Mapped[str | None] = mapped_column(Text)
    physical_page_number: Mapped[int] = mapped_column(Integer)
    printed_page_label: Mapped[str | None] = mapped_column(String(64))
    evidence_quote: Mapped[str] = mapped_column(Text)
    evidence_start_offset: Mapped[int | None] = mapped_column(Integer)
    evidence_end_offset: Mapped[int | None] = mapped_column(Integer)
    evidence_status: Mapped[str] = mapped_column(String(32), index=True)
    evidence_failure_reason: Mapped[str | None] = mapped_column(Text)
    verification_method: Mapped[str] = mapped_column(String(32))
    verification_similarity: Mapped[float] = mapped_column(Float)
    classification_eligible: Mapped[bool] = mapped_column(Boolean, index=True)
    classification_exclusion_reason: Mapped[str | None] = mapped_column(Text)
    extraction_confidence: Mapped[dict[str, Any]] = mapped_column(JSON)
    evidence_confidence: Mapped[dict[str, Any]] = mapped_column(JSON)
    normalized_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class RelationshipRow(Base):
    __tablename__ = "relationships"
    __table_args__ = (UniqueConstraint("fact_a_id", "fact_b_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    fact_a_id: Mapped[str] = mapped_column(ForeignKey("facts.id", ondelete="CASCADE"))
    fact_b_id: Mapped[str] = mapped_column(ForeignKey("facts.id", ondelete="CASCADE"))
    classification: Mapped[str] = mapped_column(String(32), index=True)
    reconciliation_reasons: Mapped[list[str]] = mapped_column(JSON)
    classification_confidence: Mapped[dict[str, Any]] = mapped_column(JSON)
    reasoning_trace: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
