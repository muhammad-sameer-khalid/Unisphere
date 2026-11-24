
from sqlalchemy.orm import Session

from app.models import AttendanceSession, Registration


def validate_attendance_record(
    db: Session,
    session_id: int,
    registration_id: int,
) -> None:
    """Ensure attendance session and registration belong to the same offering."""

    attendance_session = db.get(AttendanceSession, session_id)

    if attendance_session is None:
        raise ValueError("Attendance session does not exist.")

    registration = db.get(Registration, registration_id)

    if registration is None:
        raise ValueError("Student registration does not exist.")

    if attendance_session.offering_id != registration.offering_id:
        raise ValueError(
            "Attendance session and student registration must belong "
            "to the same course offering."
        )
