
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class CourseOffering(Base):
    __tablename__ = "course_offerings"

    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "semester_id",
            "section_code",
            name="uq_course_offerings_course_semester_section",
        ),
        CheckConstraint(
            "seat_capacity IS NULL OR seat_capacity > 0",
            name="positive_seat_capacity",
        ),
    )

    offering_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id"), nullable=False
    )
    semester_id: Mapped[int] = mapped_column(
        ForeignKey("semesters.semester_id"), nullable=False
    )
    grading_scheme_id: Mapped[int] = mapped_column(
        ForeignKey("grading_schemes.grading_scheme_id"), nullable=False
    )
    section_code: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="A"
    )
    seat_capacity: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    course: Mapped["Course"] = relationship()
    semester: Mapped["Semester"] = relationship()
    grading_scheme: Mapped["GradingScheme"] = relationship()

    faculty_assignments: Mapped[list["FacultyAssignment"]] = relationship(
        back_populates="offering"
    )
    # Registrations belonging to this course offering
    registrations: Mapped[list["Registration"]] = relationship(
        back_populates="offering"
    )
    assessments: Mapped[list["Assessment"]] = relationship(
    back_populates="offering"
    ) 
    attendance_sessions: Mapped[list["AttendanceSession"]] = relationship(
    back_populates="offering"
    )

class FacultyAssignment(Base):
    __tablename__ = "faculty_assignments"

    __table_args__ = (
        UniqueConstraint(
            "offering_id",
            "faculty_id",
            name="uq_faculty_assignments_offering_faculty",
        ),
    )

    assignment_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    offering_id: Mapped[int] = mapped_column(
        ForeignKey("course_offerings.offering_id"), nullable=False
    )
    faculty_id: Mapped[int] = mapped_column(
        ForeignKey("faculty.faculty_id"), nullable=False
    )

    offering: Mapped["CourseOffering"] = relationship(
        back_populates="faculty_assignments"
    )
    faculty: Mapped["Faculty"] = relationship(
        back_populates="faculty_assignments"
    )


class CoursePrerequisite(Base):
    __tablename__ = "course_prerequisites"

    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "prerequisite_course_id",
            name="uq_course_prerequisites_course_pair",
        ),
        CheckConstraint(
            "course_id <> prerequisite_course_id",
            name="different_prerequisite_courses",
        ),
    )

    prerequisite_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id"), nullable=False
    )
    prerequisite_course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id"), nullable=False
    )

    course: Mapped["Course"] = relationship(
        foreign_keys=[course_id]
    )
    prerequisite_course: Mapped["Course"] = relationship(
        foreign_keys=[prerequisite_course_id]
    )
