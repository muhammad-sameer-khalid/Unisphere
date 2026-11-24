from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Faculty(Base):
    __tablename__ = "faculty"

    faculty_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), nullable=False, unique=True
    )
    employee_number: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True
    )
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.department_id"), nullable=False
    )
    designation: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    user: Mapped["User"] = relationship()
    department: Mapped["Department"] = relationship()
    faculty_assignments: Mapped[list["FacultyAssignment"]] = relationship(
        back_populates="faculty"
    )