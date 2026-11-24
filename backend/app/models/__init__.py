
from app.models.user import User, Role, UserRole
from app.models.student import Student
from app.models.faculty import Faculty
from app.models.academic import Department, Program, Course, Semester
from app.models.grading import GradingScheme, GradeBand
from app.models.course_offering import (
    CourseOffering,
    FacultyAssignment,
    CoursePrerequisite,
)
from app.models.registration import Registration
from app.models.assessment import Assessment, AssessmentResult
from app.models.course_result import CourseResult
from app.models.attendance import AttendanceSession, AttendanceRecord
from app.models.fee import FeeRecord, FeePaymentRecord
from app.models.announcement import Announcement, AnnouncementAudience
from app.models.document import Document, DocumentChunk
from app.models.audit_log import AuditLog
