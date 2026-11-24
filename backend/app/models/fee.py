
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class FeeRecord(Base):
    __tablename__ = "fee_records"

    __table_args__ = (
        CheckConstraint(
            "total_charges >= 0",
            name="nonnegative_total_charges",
        ),
    )

    fee_record_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id"), nullable=False
    )
    fee_description: Mapped[str] = mapped_column(
        String(150), nullable=False
    )
    total_charges: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    due_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    student: Mapped["Student"] = relationship(
        back_populates="fee_records"
    )
    created_by: Mapped["User"] = relationship()
    payments: Mapped[list["FeePaymentRecord"]] = relationship(
        back_populates="fee_record"
    )


class FeePaymentRecord(Base):
    __tablename__ = "fee_payment_records"

    __table_args__ = (
        CheckConstraint(
            "amount_paid > 0",
            name="positive_amount_paid",
        ),
    )

    payment_record_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    fee_record_id: Mapped[int] = mapped_column(
        ForeignKey("fee_records.fee_record_id"), nullable=False
    )
    recorded_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), nullable=False
    )
    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    payment_date: Mapped[date] = mapped_column(
        Date, nullable=False
    )
    reference_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    fee_record: Mapped["FeeRecord"] = relationship(
        back_populates="payments"
    )
    recorded_by: Mapped["User"] = relationship()
