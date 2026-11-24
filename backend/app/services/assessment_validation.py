
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Assessment, Registration


def validate_assessment_result(
    db: Session,
    assessment_id: int,
    registration_id: int,
    obtained_marks: Decimal,
) -> None:
    """
    Validate an assessment result before saving it.

    Rules:
    1. Assessment must exist.
    2. Student registration must exist.
    3. Assessment and registration must belong to the same course offering.
    4. Obtained marks must be between zero and maximum marks.
    """

    assessment = db.get(Assessment, assessment_id)

    if assessment is None:
        raise ValueError("Assessment does not exist.")

    registration = db.get(Registration, registration_id)

    if registration is None:
        raise ValueError("Student registration does not exist.")

    if assessment.offering_id != registration.offering_id:
        raise ValueError(
            "Assessment and student registration must belong "
            "to the same course offering."
        )

    marks = Decimal(str(obtained_marks))

    if marks < 0:
        raise ValueError("Obtained marks cannot be negative.")

    if marks > assessment.maximum_marks:
        raise ValueError(
            f"Obtained marks cannot exceed maximum marks "
            f"({assessment.maximum_marks})."
        )
