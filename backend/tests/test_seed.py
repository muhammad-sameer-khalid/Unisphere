"""
Automated Test Suite for Task 1 — Seed Data and Synthetic Test Accounts.

Unit Tests (Database-independent):
1. Argon2 password hashing integrity for synthetic accounts.
2. CLI target safety verification (strictly enforcing local development targets; rejecting Neon, remote hosts, production, and test databases).
3. Integration test target safety (strictly enforcing local disposable PostgreSQL targets; rejecting Neon, remote hosts, and production names).
4. User identity conflict detection (distinct username vs email).
5. Faculty identity conflict detection (employee_number vs user_id).
6. Student identity conflict detection (registration_number vs user_id).
7. Ambiguous seed record detection for non-unique entities.
8. Password preservation regression test (existing hashes are never overwritten).
9. Transaction ownership behavior in standalone mode (db.begin).
10. Transaction ownership behavior in nested mode (db.begin_nested savepoint).

Integration Tests (Gated):
- Marked with @pytest.mark.integration.
- Only executes if TEST_DATABASE_URL is provided, points to an approved local disposable PostgreSQL database,
  and ALLOW_TEST_DB_RESET=true is explicitly set.
"""

import os
from decimal import Decimal
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.database.base import Base
from app.database.seed import DEMO_PASSWORD_PLAIN, seed_database
from app.models.academic import Course, Department, Program, Semester
from app.models.assessment import Assessment, AssessmentResult
from app.models.attendance import AttendanceSession
from app.models.course_offering import CourseOffering, FacultyAssignment
from app.models.faculty import Faculty
from app.models.fee import FeePaymentRecord, FeeRecord
from app.models.grading import GradeBand, GradingScheme
from app.models.registration import Registration
from app.models.student import Student
from app.models.user import Role, User, UserRole
from seed import verify_target_safety


# =============================================================================
# Helper: Target validation for integration testing (rejects Neon and remote)
# =============================================================================

ALLOWED_INTEGRATION_HOSTS = {"localhost", "127.0.0.1", "::1"}


def verify_integration_test_target(url: str, allow_reset: bool = False) -> None:
    """
    Strict safety check for integration test targets:
    1. Rejects empty URL or non-PostgreSQL scheme.
    2. Requires explicit opt-in allow_reset=True.
    3. Strictly requires an approved local host: 'localhost', '127.0.0.1', or '::1'.
    4. Strictly rejects ANY Neon host (*.neon.tech) and all other remote/cloud hosts.
    5. Rejects any production-like host or database name.
    6. Requires a dedicated disposable test database name containing 'test'
       (e.g. 'unisphere_test_db', 'disposable_test_db').
    """
    if not url or not isinstance(url, str):
        raise ValueError("Integration test database URL is not configured or invalid.")

    if not allow_reset:
        raise ValueError("Integration test execution denied: ALLOW_TEST_DB_RESET is not set to 'true'.")

    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    hostname = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    db_name = path.lstrip("/")

    if scheme not in ("postgresql", "postgresql+psycopg", "postgres"):
        raise ValueError(f"Integration tests require a PostgreSQL database URL, got scheme '{scheme}'.")

    if not hostname:
        raise ValueError("Integration test database URL does not specify a valid host.")

    if not db_name:
        raise ValueError("Integration test database URL does not specify a database name.")

    # Reject Neon cloud targets explicitly (including development branches)
    if "neon.tech" in hostname or "neon." in hostname:
        raise ValueError(
            f"Integration tests cannot target Neon cloud database: {hostname}. "
            "Must be a local disposable instance."
        )

    # Reject any production naming in host or database
    host_parts = hostname.split(".")
    if "production" in hostname or "production" in path or any("prod" in part for part in host_parts):
        raise ValueError(f"Integration tests cannot target production environment: {hostname}")

    if "production" in db_name or db_name.startswith("prod") or db_name.endswith("_prod") or "_prod_" in db_name:
        raise ValueError(f"Integration tests cannot target production-like database name: {db_name}")

    # Enforce strictly approved local hosts
    if hostname not in ALLOWED_INTEGRATION_HOSTS:
        raise ValueError(
            f"Integration tests cannot target remote database host: {hostname}. "
            "Must be an approved local disposable instance ('localhost', '127.0.0.1', or '::1')."
        )

    # Enforce test database naming to prevent wiping non-test local development databases
    if "test" not in db_name:
        raise ValueError(
            f"Integration test database name '{db_name}' must clearly indicate a disposable test database "
            "(name must contain 'test', e.g. 'unisphere_test_db' or 'disposable_test_db')."
        )


def is_safe_local_test_url(url: str | None, allow_reset: bool) -> bool:
    """Helper for pytest skipif gating."""
    if not url or not allow_reset:
        return False
    try:
        verify_integration_test_target(url, allow_reset=allow_reset)
        return True
    except Exception:
        return False


# =============================================================================
# 1. Security & Target Safety Tests (Unit)
# =============================================================================

def test_demo_password_meets_argon2_security():
    """Verify that synthetic demo password hashes to valid Argon2id with unique salts."""
    hash1 = hash_password(DEMO_PASSWORD_PLAIN)
    hash2 = hash_password(DEMO_PASSWORD_PLAIN)

    assert hash1.startswith("$argon2id$")
    assert hash2.startswith("$argon2id$")
    assert hash1 != hash2  # Unique cryptographic salt per hash
    assert verify_password(DEMO_PASSWORD_PLAIN, hash1) is True
    assert verify_password(DEMO_PASSWORD_PLAIN, hash2) is True
    assert verify_password("WrongPassword!", hash1) is False


def test_cli_target_safety_rejection_neon():
    """Verify that CLI safety verification strictly prohibits Neon cloud endpoints."""
    # Neon endpoints (even dev branches) must be rejected
    with pytest.raises(SystemExit):
        verify_target_safety("postgresql+psycopg://user:pw@ep-dev-123.us-east-2.aws.neon.tech/unisphere_dev")

    with pytest.raises(SystemExit):
        verify_target_safety("postgresql+psycopg://user:pw@neon.tech/unisphere_db")


def test_cli_target_safety_rejection_remote_hosts():
    """Verify that CLI safety verification strictly rejects remote or third-party cloud hosts."""
    with pytest.raises(SystemExit):
        verify_target_safety("postgresql+psycopg://user:pw@database.rds.amazonaws.com/unisphere_db")

    with pytest.raises(SystemExit):
        verify_target_safety("postgresql+psycopg://user:pw@custom-vps.example.com/unisphere_dev")

    with pytest.raises(SystemExit):
        verify_target_safety("postgresql+psycopg://user:pw@192.168.1.100/unisphere_db")


def test_cli_target_safety_rejection_prod_databases():
    """Verify that CLI safety verification strictly blocks production hosts and databases."""
    with pytest.raises(SystemExit):
        verify_target_safety("postgresql+psycopg://user:pw@localhost/prod_unisphere")

    with pytest.raises(SystemExit):
        verify_target_safety("postgresql+psycopg://user:pw@localhost/production_db")


def test_cli_target_safety_rejection_test_databases():
    """Verify that CLI safety verification blocks test databases."""
    with pytest.raises(SystemExit):
        verify_target_safety("postgresql+psycopg://postgres:pw@localhost:5432/unisphere_test_db")

    with pytest.raises(SystemExit):
        verify_target_safety("postgresql+psycopg://postgres:pw@localhost:5432/test_unisphere")


def test_cli_target_safety_rejection_invalid_urls():
    """Verify that CLI safety verification rejects empty, malformed, or unapproved targets."""
    with pytest.raises(SystemExit):
        verify_target_safety("")

    with pytest.raises(SystemExit):
        verify_target_safety("postgresql://")

    with pytest.raises(SystemExit):
        verify_target_safety("mysql://user:pw@localhost/unisphere_db")

    with pytest.raises(SystemExit):
        verify_target_safety("postgresql+psycopg://postgres:pw@localhost:5432/postgres")

    with pytest.raises(SystemExit):
        verify_target_safety("postgresql+psycopg://postgres:pw@localhost:5432/arbitrary_other_db")


def test_cli_target_safety_acceptance_local_targets():
    """Verify that CLI safety verification accepts explicitly approved local development targets."""
    verify_target_safety("postgresql+psycopg://postgres:pw@localhost:5432/unisphere_dev")
    verify_target_safety("postgresql+psycopg://postgres:pw@127.0.0.1:5432/unisphere_db")
    verify_target_safety("postgresql+psycopg://postgres:pw@[::1]:5432/unisphere_local")
    verify_target_safety("postgresql://postgres:pw@localhost:5432/unisphere_development")


def test_integration_target_rejection_neon():
    """Verify that integration test runner strictly rejects Neon cloud URLs."""
    with pytest.raises(ValueError, match="cannot target Neon cloud database"):
        verify_integration_test_target(
            "postgresql+psycopg://user:pw@ep-test-123.us-east-2.aws.neon.tech/unisphere_test_db",
            allow_reset=True,
        )


def test_integration_target_rejection_remote_hosts():
    """Verify that integration test runner rejects remote hosts."""
    with pytest.raises(ValueError, match="cannot target remote database host"):
        verify_integration_test_target(
            "postgresql+psycopg://user:pw@my-remote-db.rds.amazonaws.com:5432/unisphere_test_db",
            allow_reset=True,
        )


def test_integration_target_rejection_without_reset_flag():
    """Verify that integration test runner requires ALLOW_TEST_DB_RESET=true."""
    with pytest.raises(ValueError, match="ALLOW_TEST_DB_RESET is not set"):
        verify_integration_test_target(
            "postgresql+psycopg://postgres:pw@localhost:5432/unisphere_test_db",
            allow_reset=False,
        )


def test_integration_target_rejection_non_disposable_names():
    """Verify that integration test runner rejects non-test or production database names."""
    with pytest.raises(ValueError, match="must clearly indicate a disposable test database"):
        verify_integration_test_target(
            "postgresql+psycopg://postgres:pw@localhost:5432/unisphere_dev",
            allow_reset=True,
        )

    with pytest.raises(ValueError, match="cannot target production"):
        verify_integration_test_target(
            "postgresql+psycopg://postgres:pw@localhost:5432/production_test_db",
            allow_reset=True,
        )


def test_integration_target_acceptance_local_disposable():
    """Verify that integration test runner accepts local disposable test targets."""
    verify_integration_test_target(
        "postgresql+psycopg://postgres:pw@localhost:5432/unisphere_test_db",
        allow_reset=True,
    )
    verify_integration_test_target(
        "postgresql+psycopg://postgres:pw@127.0.0.1:5432/disposable_test_db",
        allow_reset=True,
    )
    verify_integration_test_target(
        "postgresql+psycopg://postgres:pw@[::1]:5432/my_test_database",
        allow_reset=True,
    )


# =============================================================================
# 2. Identity Resolution & Conflict Detection Tests (Mock/Unit)
# =============================================================================

def test_user_identity_conflict_detection():
    """
    Verify that if a username matches one existing user and the email matches
    a DIFFERENT existing user, seed_database aborts with ValueError to prevent
    corrupting or cross-linking accounts.
    """
    mock_db = MagicMock(spec=Session)
    mock_db.in_transaction.return_value = False

    roles = [Role(role_id=i, role_name=n) for i, n in enumerate(["Administrator", "Faculty", "Student", "Finance Personnel"], 1)]
    mock_db.scalar.side_effect = [
        roles[0], roles[1], roles[2], roles[3],  # 4 roles
        User(user_id=101, username="admin_demo", email="old_admin@example.test"),  # user_by_uname
        User(user_id=202, username="other_user", email="admin@unisphere.example.test"),  # user_by_email
    ]

    with pytest.raises(ValueError, match="User identity conflict"):
        seed_database(mock_db)


def test_faculty_identity_conflict_detection():
    """Verify that conflicting employee_number and user_id raises ValueError."""
    mock_db = MagicMock(spec=Session)
    mock_db.in_transaction.return_value = False

    roles = [Role(role_id=i, role_name=n) for i, n in enumerate(["Administrator", "Faculty", "Student", "Finance Personnel"], 1)]
    admin_user = User(user_id=1, username="admin_demo", email="admin@unisphere.example.test")
    faculty_user = User(user_id=2, username="faculty_demo", email="faculty.cs@unisphere.example.test")
    student1_user = User(user_id=3, username="student1_demo", email="student1@unisphere.example.test")
    student2_user = User(user_id=4, username="student2_demo", email="student2@unisphere.example.test")
    finance_user = User(user_id=5, username="finance_demo", email="finance@unisphere.example.test")

    mock_db.scalar.side_effect = [
        # Roles (4)
        roles[0], roles[1], roles[2], roles[3],
        # Users (admin_demo: uname, email, user_role)
        admin_user, admin_user, None,
        # faculty_demo: uname, email, user_role
        faculty_user, faculty_user, None,
        # student1_demo
        student1_user, student1_user, None,
        # student2_demo
        student2_user, student2_user, None,
        # finance_demo
        finance_user, finance_user, None,
        # Department
        Department(department_id=1, department_code="CS"),
        # Courses (2)
        None, None,
        # Semester
        None,
        # Faculty lookup: fac_by_emp returns ID 10, fac_by_user returns ID 20 (conflict!)
        Faculty(faculty_id=10, employee_number="EMP-CS-001", user_id=99),
        Faculty(faculty_id=20, employee_number="EMP-OTHER", user_id=2),
    ]

    def mock_scalars(statement):
        mock_res = MagicMock()
        stmt_str = str(statement)
        if "programs" in stmt_str:
            mock_res.all.return_value = [Program(program_id=1, program_name="Bachelor of Science in Computer Science")]
        elif "grading_schemes" in stmt_str:
            mock_res.all.return_value = [GradingScheme(grading_scheme_id=1, scheme_name="Demo Standard Letter Grading Scheme")]
        elif "grade_bands" in stmt_str:
            mock_res.all.return_value = [GradeBand(grade_band_id=1, letter_grade="A")]
        else:
            mock_res.all.return_value = []
        return mock_res

    mock_db.scalars.side_effect = mock_scalars

    with pytest.raises(ValueError, match="Faculty identity conflict"):
        seed_database(mock_db)


def test_student_identity_conflict_detection():
    """Verify that conflicting registration_number and user_id raises ValueError."""
    mock_db = MagicMock(spec=Session)
    mock_db.in_transaction.return_value = False

    roles = [Role(role_id=i, role_name=n) for i, n in enumerate(["Administrator", "Faculty", "Student", "Finance Personnel"], 1)]
    admin_user = User(user_id=1, username="admin_demo", email="admin@unisphere.example.test")
    faculty_user = User(user_id=2, username="faculty_demo", email="faculty.cs@unisphere.example.test")
    student1_user = User(user_id=3, username="student1_demo", email="student1@unisphere.example.test")
    student2_user = User(user_id=4, username="student2_demo", email="student2@unisphere.example.test")
    finance_user = User(user_id=5, username="finance_demo", email="finance@unisphere.example.test")

    mock_db.scalar.side_effect = [
        # Roles (4)
        roles[0], roles[1], roles[2], roles[3],
        # Users (5 users x 3 queries: uname, email, user_role)
        admin_user, admin_user, None,
        faculty_user, faculty_user, None,
        student1_user, student1_user, None,
        student2_user, student2_user, None,
        finance_user, finance_user, None,
        # Department
        Department(department_id=1, department_code="CS"),
        # Courses (2)
        None, None,
        # Semester
        None,
        # Faculty (fac_by_emp, fac_by_user match same faculty ID 10)
        Faculty(faculty_id=10, employee_number="EMP-CS-001", user_id=2),
        Faculty(faculty_id=10, employee_number="EMP-CS-001", user_id=2),
        # Student 1 lookup: st_by_reg returns ID 100, st_by_user returns ID 200 (conflict!)
        Student(student_id=100, registration_number="2022-CS-001", user_id=88),
        Student(student_id=200, registration_number="2022-CS-OTHER", user_id=3),
    ]

    def mock_scalars(statement):
        mock_res = MagicMock()
        stmt_str = str(statement)
        if "programs" in stmt_str:
            mock_res.all.return_value = [Program(program_id=1, program_name="Bachelor of Science in Computer Science")]
        elif "grading_schemes" in stmt_str:
            mock_res.all.return_value = [GradingScheme(grading_scheme_id=1, scheme_name="Demo Standard Letter Grading Scheme")]
        elif "grade_bands" in stmt_str:
            mock_res.all.return_value = [GradeBand(grade_band_id=1, letter_grade="A")]
        else:
            mock_res.all.return_value = []
        return mock_res

    mock_db.scalars.side_effect = mock_scalars

    with pytest.raises(ValueError, match="Student identity conflict"):
        seed_database(mock_db)


def test_ambiguous_seed_match_detection():
    """Verify that multiple matching records for non-unique entities raises ValueError."""
    mock_db = MagicMock(spec=Session)
    mock_db.in_transaction.return_value = False

    roles = [Role(role_id=i, role_name=n) for i, n in enumerate(["Administrator", "Faculty", "Student", "Finance Personnel"], 1)]
    mock_user = User(user_id=1, username="admin_demo", email="admin@unisphere.example.test")
    mock_dept = Department(department_id=1, department_code="CS")

    mock_db.scalar.side_effect = [
        roles[0], roles[1], roles[2], roles[3],  # 4 roles
        # 5 users (uname, email, user_role)
        mock_user, mock_user, None,
        mock_user, mock_user, None,
        mock_user, mock_user, None,
        mock_user, mock_user, None,
        mock_user, mock_user, None,
        mock_dept,  # department
    ]

    # Return TWO programs matching the department and name (ambiguity)
    mock_db.scalars.return_value.all.return_value = [
        Program(program_id=1, program_name="Bachelor of Science in Computer Science"),
        Program(program_id=2, program_name="Bachelor of Science in Computer Science"),
    ]

    with pytest.raises(ValueError, match="Ambiguous seed match: multiple programs found"):
        seed_database(mock_db)


# =============================================================================
# 3. Password Preservation Regression Test
# =============================================================================

def test_password_hash_never_overwritten_for_existing_user():
    """
    Regression test: When a user already exists in the database,
    seed_database must NEVER overwrite or regenerate their password_hash.
    """
    existing_hash = "$argon2id$v=19$m=65536,t=3,p=4$PreExistingHashValue12345"
    existing_user = User(
        user_id=10,
        username="admin_demo",
        email="admin@unisphere.example.test",
        password_hash=existing_hash,
    )

    mock_db = MagicMock(spec=Session)
    mock_db.in_transaction.return_value = False

    roles = [Role(role_id=i, role_name=n) for i, n in enumerate(["Administrator", "Faculty", "Student", "Finance Personnel"], 1)]
    mock_db.scalar.side_effect = [
        roles[0], roles[1], roles[2], roles[3],  # 4 roles
        existing_user,  # user_by_uname
        existing_user,  # user_by_email
        None,  # user_role
        RuntimeError("Stop seed here for unit test assertion"),
    ]

    with patch("app.database.seed.hash_password") as mock_hash:
        try:
            seed_database(mock_db)
        except RuntimeError:
            pass

        # Confirm that hash_password was never invoked for this existing user
        mock_hash.assert_not_called()
        assert existing_user.password_hash == existing_hash


# =============================================================================
# 4. Transaction Ownership & Rollback Unit Tests (Without Database)
# =============================================================================

def test_transaction_ownership_standalone_mode():
    """Verify that when db is not in a transaction, seed_database begins a top-level transaction."""
    mock_db = MagicMock(spec=Session)
    mock_db.in_transaction.return_value = False

    mock_db.scalar.side_effect = RuntimeError("Simulated failure inside transaction")

    with pytest.raises(RuntimeError, match="Simulated failure inside transaction"):
        seed_database(mock_db)

    # Top-level begin was called (not begin_nested)
    mock_db.begin.assert_called_once()
    mock_db.begin_nested.assert_not_called()


def test_transaction_ownership_nested_mode():
    """Verify that when db is ALREADY in a transaction, seed_database uses begin_nested (savepoint)."""
    mock_db = MagicMock(spec=Session)
    mock_db.in_transaction.return_value = True

    mock_db.scalar.side_effect = RuntimeError("Simulated failure inside savepoint")

    with pytest.raises(RuntimeError, match="Simulated failure inside savepoint"):
        seed_database(mock_db)

    # Savepoint was created, top-level transaction was untouched
    mock_db.begin_nested.assert_called_once()
    mock_db.begin.assert_not_called()


# =============================================================================
# 5. Live PostgreSQL Integration Tests (Safely Gated — DO NOT EXECUTE NOW)
# =============================================================================

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")
ALLOW_RESET = os.getenv("ALLOW_TEST_DB_RESET", "false").lower() == "true"


@pytest.mark.integration
@pytest.mark.skipif(
    not is_safe_local_test_url(TEST_DB_URL, ALLOW_RESET),
    reason="Live PostgreSQL integration tests require a validated local disposable TEST_DATABASE_URL and ALLOW_TEST_DB_RESET=true.",
)
def test_live_postgresql_seed_integration():
    """
    Live PostgreSQL integration test executed against a verified local disposable test database.
    DO NOT EXECUTE during Task 1 verification — gated by runtime check and skipif condition.

    Verifies:
    1. Seed transaction rollback contract:
       Pre-existing identity conflict causes seed_database to abort; verifies that partial
       seed entities created prior to failure (roles) are rolled back and not persisted.
    2. Complete seed run creates all synthetic entities matching exact expected counts:
       - Roles: 4, Users: 5, User roles: 5, Departments: 1, Programs: 1, Courses: 2,
       - Semesters: 1, Grading schemes: 1, Grade bands: 6, Faculty: 1, Students: 2,
       - Course offerings: 2, Faculty assignments: 2, Registrations: 3, Assessments: 1,
       - Assessment results: 1, Attendance sessions: 1, Fee records: 1, Fee payment records: 1.
    3. Password verification:
       All 5 demo accounts exist, have valid Argon2id hashes, and authenticate with demo password.
    4. Second seed run is strictly idempotent: 0 records created, existing records preserved.
    5. Password hash preservation:
       Modifying a user's password to a custom hash is preserved across subsequent seed runs.
    6. Nested transaction savepoint behavior:
       seed_database operates correctly inside an outer transaction without interfering with outer scope.
    """
    # 0. Strict runtime safety verification before any connection or table operation
    verify_integration_test_target(TEST_DB_URL, allow_reset=ALLOW_RESET)

    engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
    try:
        # Clean slate on dedicated disposable test database
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        with Session(bind=engine) as session:
            # -------------------------------------------------------------
            # Phase 1: Test Seed Rollback Behavior on Failure
            # -------------------------------------------------------------
            # Pre-insert two conflicting users to trigger User identity conflict during seed_database
            conflict_user1 = User(
                username="admin_demo",
                email="admin_other@unisphere.example.test",
                password_hash=hash_password("ConflictPassword123!"),
                is_active=True,
            )
            conflict_user2 = User(
                username="other_admin",
                email="admin@unisphere.example.test",
                password_hash=hash_password("ConflictPassword123!"),
                is_active=True,
            )
            with session.begin():
                session.add(conflict_user1)
                session.add(conflict_user2)

            # seed_database in standalone mode creates roles first, then fails on admin_demo
            with pytest.raises(ValueError, match="User identity conflict"):
                seed_database(session)

            # Close any implicit transaction and verify that the 4 roles created before failure were rolled back
            session.rollback()
            for r_name in ["Administrator", "Faculty", "Student", "Finance Personnel"]:
                assert session.scalar(select(Role).where(Role.role_name == r_name)) is None

            # Clean test database for fresh initial seed run
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)

            # -------------------------------------------------------------
            # Phase 2: Initial Seed Execution (Verify Creation Counts)
            # -------------------------------------------------------------
            stats_run1 = seed_database(session)

            assert stats_run1["roles"]["created"] == 4
            assert stats_run1["users"]["created"] == 5
            assert stats_run1["user_roles"]["created"] == 5
            assert stats_run1["departments"]["created"] == 1
            assert stats_run1["programs"]["created"] == 1
            assert stats_run1["courses"]["created"] == 2
            assert stats_run1["semesters"]["created"] == 1
            assert stats_run1["grading_schemes"]["created"] == 1
            assert stats_run1["grade_bands"]["created"] == 6
            assert stats_run1["faculty"]["created"] == 1
            assert stats_run1["students"]["created"] == 2
            assert stats_run1["course_offerings"]["created"] == 2
            assert stats_run1["faculty_assignments"]["created"] == 2
            assert stats_run1["registrations"]["created"] == 3
            assert stats_run1["assessments"]["created"] == 1
            assert stats_run1["assessment_results"]["created"] == 1
            assert stats_run1["attendance_sessions"]["created"] == 1
            assert stats_run1["fee_records"]["created"] == 1
            assert stats_run1["fee_payment_records"]["created"] == 1

            # -------------------------------------------------------------
            # Phase 3: Password Verification for All Synthetic Accounts
            # -------------------------------------------------------------
            demo_usernames = [
                "admin_demo",
                "faculty_demo",
                "student1_demo",
                "student2_demo",
                "finance_demo",
            ]
            for uname in demo_usernames:
                user = session.scalar(select(User).where(User.username == uname))
                assert user is not None, f"Synthetic demo user '{uname}' was not found in database."
                assert user.password_hash.startswith("$argon2id$")
                assert verify_password(DEMO_PASSWORD_PLAIN, user.password_hash) is True

            # -------------------------------------------------------------
            # Phase 4: Second Seed Execution (Verify Idempotency)
            # -------------------------------------------------------------
            stats_run2 = seed_database(session)
            for entity_name, counts in stats_run2.items():
                assert counts["created"] == 0, f"Entity '{entity_name}' created unexpected records on run 2"
                assert counts["existing"] > 0, f"Entity '{entity_name}' did not detect existing records on run 2"

            # -------------------------------------------------------------
            # Phase 5: Password Hash Preservation (Custom Hash Regression)
            # -------------------------------------------------------------
            custom_plain = "StudentCustom#Secure2026"
            custom_hash = hash_password(custom_plain)
            student1 = session.scalar(select(User).where(User.username == "student1_demo"))
            assert student1 is not None
            student1.password_hash = custom_hash
            session.commit()

            stats_run3 = seed_database(session)
            assert stats_run3["users"]["created"] == 0
            session.expire_all()
            student1_reloaded = session.scalar(select(User).where(User.username == "student1_demo"))
            assert student1_reloaded.password_hash == custom_hash
            assert verify_password(custom_plain, student1_reloaded.password_hash) is True

            # -------------------------------------------------------------
            # Phase 6: Nested Transaction / Savepoint Contract
            # -------------------------------------------------------------
            # Execute within an outer transaction to verify savepoint behavior
            with session.begin():
                stats_nested = seed_database(session)
                assert stats_nested["users"]["created"] == 0
                assert stats_nested["roles"]["created"] == 0

    finally:
        try:
            Base.metadata.drop_all(bind=engine)
        finally:
            engine.dispose()
