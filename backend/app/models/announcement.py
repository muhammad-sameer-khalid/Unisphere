
from datetime import datetime

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


class Announcement(Base):
    __tablename__ = "announcements"

    announcement_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    publisher_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), nullable=False
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    publication_status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    publisher: Mapped["User"] = relationship()
    audiences: Mapped[list["AnnouncementAudience"]] = relationship(
        back_populates="announcement"
    )


class AnnouncementAudience(Base):
    __tablename__ = "announcement_audiences"

    __table_args__ = (
        UniqueConstraint(
            "announcement_id",
            "audience_type",
            name="uq_announcement_audiences_announcement_type",
        ),
    )

    audience_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    announcement_id: Mapped[int] = mapped_column(
        ForeignKey("announcements.announcement_id"), nullable=False
    )
    audience_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )

    announcement: Mapped["Announcement"] = relationship(
        back_populates="audiences"
    )
