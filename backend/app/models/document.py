
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), nullable=False
    )
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id"), nullable=True
    )
    document_title: Mapped[str] = mapped_column(
        String(200), nullable=False
    )
    file_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    mime_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    approval_status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    uploader: Mapped["User"] = relationship(
        foreign_keys=[uploaded_by]
    )
    approver: Mapped["User | None"] = relationship(
        foreign_keys=[approved_by]
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_index",
        ),
    )

    chunk_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.document_id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    chunk_content: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    page_number: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    embedding = mapped_column(Vector())

    document: Mapped["Document"] = relationship(
        back_populates="chunks"
    )
