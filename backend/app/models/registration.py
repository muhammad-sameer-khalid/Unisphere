
from datetime import date

from sqlalchemy import (
    Date,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Registration(Base):
    __tablename__ = "registrations"

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "offering_id",
            name="uq_registrations_student_offering",
        ),
    )

    registration_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id"), nullable=False
    )
    offering_id: Mapped[int] = mapped_column(
        ForeignKey("course_offerings.offering_id"), nullable=False
    )
    registration_date: Mapped[date] = mapped_column(
        Date, nullable=False
    )
    registration_status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    student: Mapped["Student"] = relationship(
        back_populates="registrations"
    )
    offering: Mapped["CourseOffering"] = relationship(
        back_populates="registrations"
    )
    assessment_results: Mapped[list["AssessmentResult"]] = relationship(
    back_populates="registration"
    )
    course_result: Mapped["CourseResult | None"] = relationship(
    back_populates="registration",
    uselist=False,
    )
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
    back_populates="registration"
    )