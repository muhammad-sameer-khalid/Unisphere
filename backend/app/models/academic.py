
from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Department(Base):
    __tablename__ = "departments"

    department_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    department_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    department_code: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True
    )

    programs: Mapped[list["Program"]] = relationship(
        back_populates="department"
    )
    courses: Mapped[list["Course"]] = relationship(
        back_populates="department"
    )
    faculty_members: Mapped[list["Faculty"]] = relationship(
        back_populates="department"
    )


class Program(Base):
    __tablename__ = "programs"

    program_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.department_id"), nullable=False
    )
    program_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    degree_level: Mapped[str] = mapped_column(
        String(30), nullable=False
    )

    department: Mapped["Department"] = relationship(
        back_populates="programs"
    )
    students: Mapped[list["Student"]] = relationship(
        back_populates="program"
    )


class Course(Base):
    __tablename__ = "courses"

    __table_args__ = (
        CheckConstraint(
            "credit_hours > 0",
            name="positive_credit_hours"
        ),
    )

    course_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.department_id"), nullable=False
    )
    course_code: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True
    )
    course_title: Mapped[str] = mapped_column(
        String(150), nullable=False
    )
    credit_hours: Mapped[float] = mapped_column(
        Numeric(3, 1), nullable=False
    )

    department: Mapped["Department"] = relationship(
        back_populates="courses"
    )


class Semester(Base):
    __tablename__ = "semesters"

    __table_args__ = (
        UniqueConstraint(
            "semester_name",
            "academic_year",
            name="uq_semesters_name_year"
        ),
        CheckConstraint(
            "end_date >= start_date",
            name="valid_semester_dates"
        ),
    )

    semester_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    semester_name: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    academic_year: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    start_date: Mapped[date] = mapped_column(
        Date, nullable=False
    )
    end_date: Mapped[date] = mapped_column(
        Date, nullable=False
    )
