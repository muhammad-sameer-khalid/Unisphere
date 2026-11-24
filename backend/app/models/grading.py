from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class GradingScheme(Base):
    __tablename__ = "grading_schemes"

    grading_scheme_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    scheme_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    grade_bands: Mapped[list["GradeBand"]] = relationship(
        back_populates="grading_scheme"
    )


class GradeBand(Base):
    __tablename__ = "grade_bands"

    __table_args__ = (
        UniqueConstraint(
            "grading_scheme_id",
            "grade_band_id",
            name="uq_grade_bands_scheme_band"
        ),
        CheckConstraint(
            "minimum_marks <= maximum_marks",
            name="valid_grade_band_range"
        ),
    )

    grade_band_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    grading_scheme_id: Mapped[int] = mapped_column(
        ForeignKey("grading_schemes.grading_scheme_id"), nullable=False
    )
    minimum_marks: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    maximum_marks: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    letter_grade: Mapped[str] = mapped_column(
        String(5), nullable=False
    )
    grade_points: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False
    )

    grading_scheme: Mapped["GradingScheme"] = relationship(
        back_populates="grade_bands"
    )
    course_results: Mapped[list["CourseResult"]] = relationship(
        back_populates="grade_band",
        foreign_keys="CourseResult.grade_band_id",
    )