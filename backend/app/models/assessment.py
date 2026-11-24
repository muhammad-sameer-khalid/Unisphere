
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Assessment(Base):
    __tablename__ = "assessments"

    __table_args__ = (
        CheckConstraint(
            "maximum_marks > 0",
            name="positive_maximum_marks",
        ),
        CheckConstraint(
            "weightage >= 0 AND weightage <= 100",
            name="valid_weightage",
        ),
    )

    assessment_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    offering_id: Mapped[int] = mapped_column(
        ForeignKey("course_offerings.offering_id"), nullable=False
    )
    assessment_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    assessment_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    maximum_marks: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False
    )
    weightage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )

    offering: Mapped["CourseOffering"] = relationship(
        back_populates="assessments"
    )
    assessment_results: Mapped[list["AssessmentResult"]] = relationship(
        back_populates="assessment"
    )


class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "registration_id",
            name="uq_assessment_results_assessment_registration",
        ),
        CheckConstraint(
            "obtained_marks >= 0",
            name="nonnegative_obtained_marks",
        ),
    )

    result_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.assessment_id"), nullable=False
    )
    registration_id: Mapped[int] = mapped_column(
        ForeignKey("registrations.registration_id"), nullable=False
    )
    obtained_marks: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False
    )
    entered_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    assessment: Mapped["Assessment"] = relationship(
        back_populates="assessment_results"
    )
    registration: Mapped["Registration"] = relationship(
        back_populates="assessment_results"
    )
