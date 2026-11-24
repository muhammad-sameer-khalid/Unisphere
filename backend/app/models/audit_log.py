
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id"), nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    entity_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    record_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    action_timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )

    user: Mapped["User | None"] = relationship()
