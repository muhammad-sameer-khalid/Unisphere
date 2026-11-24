from sqlalchemy import ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Student(Base):
    __tablename__ = "students"

    student_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), nullable=False, unique=True
    )
    registration_number: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True
    )
    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.program_id"), nullable=False
    )
    current_semester_number: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )

    user: Mapped["User"] = relationship()
    program: Mapped["Program"] = relationship()
    registrations: Mapped[list["Registration"]] = relationship(
        back_populates="student"
    )
    fee_records: Mapped[list["FeeRecord"]] = relationship(
        back_populates="student"
    )