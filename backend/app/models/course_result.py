
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class CourseResult(Base):
    __tablename__ = "course_results"

    __table_args__ = (
        UniqueConstraint(
            "registration_id",
            name="uq_course_results_registration",
        ),
        ForeignKeyConstraint(
            ["grading_scheme_id", "grade_band_id"],
            [
                "grade_bands.grading_scheme_id",
                "grade_bands.grade_band_id",
            ],
            name="fk_course_results_scheme_grade_band",
        ),
        CheckConstraint(
            "total_marks >= 0",
            name="nonnegative_total_marks",
        ),
    )

    course_result_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    registration_id: Mapped[int] = mapped_column(
        ForeignKey("registrations.registration_id"), nullable=False
    )
    grading_scheme_id: Mapped[int] = mapped_column(
        ForeignKey("grading_schemes.grading_scheme_id"), nullable=False
    )
    grade_band_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    total_marks: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False
    )
    result_status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    finalized_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id"), nullable=True
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    published_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id"), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    registration: Mapped["Registration"] = relationship(
        back_populates="course_result"
    )
    grading_scheme: Mapped["GradingScheme"] = relationship(
        foreign_keys=[grading_scheme_id]
    )

    grade_band: Mapped["GradeBand | None"] = relationship(
        back_populates="course_results",
        foreign_keys=[grade_band_id],
    )
    finalized_by: Mapped["User | None"] = relationship(
        foreign_keys=[finalized_by_user_id]
    )
    published_by: Mapped["User | None"] = relationship(
        foreign_keys=[published_by_user_id]
    )
