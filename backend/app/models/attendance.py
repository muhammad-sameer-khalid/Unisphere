
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    session_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    offering_id: Mapped[int] = mapped_column(
        ForeignKey("course_offerings.offering_id"), nullable=False
    )
    session_date: Mapped[date] = mapped_column(
        Date, nullable=False
    )
    topic: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )

    offering: Mapped["CourseOffering"] = relationship(
        back_populates="attendance_sessions"
    )
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        back_populates="session"
    )


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "registration_id",
            name="uq_attendance_records_session_registration",
        ),
    )

    attendance_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    session_id: Mapped[int] = mapped_column(
        ForeignKey("attendance_sessions.session_id"), nullable=False
    )
    registration_id: Mapped[int] = mapped_column(
        ForeignKey("registrations.registration_id"), nullable=False
    )
    attendance_status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    session: Mapped["AttendanceSession"] = relationship(
        back_populates="attendance_records"
    )
    registration: Mapped["Registration"] = relationship(
        back_populates="attendance_records"
    )
