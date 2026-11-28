"""
UniSphere Seed Data and Synthetic Test Accounts Module.

Provides an idempotent, transaction-safe seeding mechanism that populates
the database with consistent synthetic records for development, testing,
and demonstration.

Transaction Ownership Contract:
1. Standalone Execution (CLI):
   When `not db.in_transaction()`, `seed_database` starts and owns a top-level
   transaction via `db.begin()`. Exiting the context block commits the transaction.
   Any unhandled exception rolls back the entire transaction.
2. Nested Execution (Integration Tests / Outer Transaction):
   When `db.in_transaction()` is True, `seed_database` issues `db.begin_nested()`,
   creating a database SAVEPOINT.
   Important SQLAlchemy behavior: `begin_nested()` flushes any currently pending
   session operations before establishing the savepoint. Rolling back this savepoint
   reverses only the operations executed *within* this nested block; it does not
   reverse operations flushed or committed prior to the savepoint. The outer caller
   remains responsible for committing or rolling back the outer transaction.

Identity Resolution & Data Integrity Rules:
- Username and email are resolved independently. If they match different existing
  users, seeding raises a ValueError to prevent silent account corruption.
- Equivalent conflict detection applies to Faculty (employee_number vs user_id)
  and Student (registration_number vs user_id).
- Existing user password hashes are NEVER overwritten.
- For entities without database uniqueness constraints (programs, grading schemes,
  assessments, attendance sessions, fee records), multiple matches trigger an
  explicit ValueError rather than picking an arbitrary record with .first().
- Attendance records (PRESENT/ABSENT) are omitted until official attendance statuses
  are formally confirmed by approved institutional requirements.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
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

# Standard synthetic demo password for synthetic demonstration accounts
DEMO_PASSWORD_PLAIN = "UniSphereDemo2026!"


def seed_database(db: Session) -> Dict[str, Dict[str, int]]:
    """
    Populate the database with synthetic demonstration data.

    Returns a summary dictionary reporting the count of created and
    existing records for each entity.

    Raises:
        ValueError: On ambiguous seed matches or conflicting identity records.
    """
    stats: Dict[str, Dict[str, int]] = {}

    def record_stat(entity: str, created: bool) -> None:
        if entity not in stats:
            stats[entity] = {"created": 0, "existing": 0}
        if created:
            stats[entity]["created"] += 1
        else:
            stats[entity]["existing"] += 1

    # Transaction ownership: savepoint if already inside outer transaction, top-level transaction otherwise
    tx_manager = db.begin_nested() if db.in_transaction() else db.begin()

    with tx_manager:
        # =====================================================================
        # 1. ROLES (DB Unique Constraint: uq_roles_role_name)
        # =====================================================================
        role_names = [
            "Administrator",
            "Faculty",
            "Student",
            "Finance Personnel",
        ]
        roles_by_name: Dict[str, Role] = {}
        for r_name in role_names:
            role = db.scalar(select(Role).where(Role.role_name == r_name))
            if not role:
                role = Role(role_name=r_name)
                db.add(role)
                db.flush()
                record_stat("roles", created=True)
            else:
                record_stat("roles", created=False)
            roles_by_name[r_name] = role

        # =====================================================================
        # 2. USERS (DB Unique Constraints: uq_users_username, uq_users_email)
        # Resolve username and email independently. Detect conflicting identities.
        # NEVER overwrite existing password hashes.
        # =====================================================================
        user_specs = [
            {
                "username": "admin_demo",
                "email": "admin@unisphere.example.test",
                "full_name": "System Administrator (Demo)",
                "role": "Administrator",
            },
            {
                "username": "faculty_demo",
                "email": "faculty.cs@unisphere.example.test",
                "full_name": "Dr. Sarah Khan (Demo)",
                "role": "Faculty",
            },
            {
                "username": "student1_demo",
                "email": "student1@unisphere.example.test",
                "full_name": "Ali Ahmed (Demo)",
                "role": "Student",
            },
            {
                "username": "student2_demo",
                "email": "student2@unisphere.example.test",
                "full_name": "Fatima Noor (Demo)",
                "role": "Student",
            },
            {
                "username": "finance_demo",
                "email": "finance@unisphere.example.test",
                "full_name": "Tariq Mahmood (Demo)",
                "role": "Finance Personnel",
            },
        ]

        users_by_username: Dict[str, User] = {}
        for spec in user_specs:
            user_by_uname = db.scalar(
                select(User).where(User.username == spec["username"])
            )
            user_by_email = db.scalar(
                select(User).where(User.email == spec["email"])
            )

            # Conflict detection: username and email belong to distinct existing records
            if (
                user_by_uname is not None
                and user_by_email is not None
                and user_by_uname.user_id != user_by_email.user_id
            ):
                raise ValueError(
                    f"User identity conflict: username '{spec['username']}' belongs to user ID "
                    f"{user_by_uname.user_id}, but email '{spec['email']}' belongs to user ID "
                    f"{user_by_email.user_id}. Aborting seed to preserve data integrity."
                )

            user = user_by_uname or user_by_email

            if not user:
                # Argon2id password hash with unique cryptographic salt
                hashed_pw = hash_password(DEMO_PASSWORD_PLAIN)
                user = User(
                    username=spec["username"],
                    email=spec["email"],
                    full_name=spec["full_name"],
                    password_hash=hashed_pw,
                    is_active=True,
                )
                db.add(user)
                db.flush()
                record_stat("users", created=True)
            else:
                record_stat("users", created=False)

            users_by_username[spec["username"]] = user

            # Assign Role via UserRole (DB Unique: uq_user_roles_user_role)
            target_role = roles_by_name[spec["role"]]
            user_role = db.scalar(
                select(UserRole).where(
                    UserRole.user_id == user.user_id,
                    UserRole.role_id == target_role.role_id,
                )
            )
            if not user_role:
                user_role = UserRole(
                    user_id=user.user_id,
                    role_id=target_role.role_id,
                )
                db.add(user_role)
                db.flush()
                record_stat("user_roles", created=True)
            else:
                record_stat("user_roles", created=False)

        # =====================================================================
        # 3. ACADEMIC STRUCTURE
        # =====================================================================
        # Department (DB Unique: uq_departments_department_code)
        dept = db.scalar(
            select(Department).where(Department.department_code == "CS")
        )
        if not dept:
            dept = Department(
                department_code="CS",
                department_name="Department of Computer Science",
            )
            db.add(dept)
            db.flush()
            record_stat("departments", created=True)
        else:
            record_stat("departments", created=False)

        # Program (No DB uniqueness constraint -> detect ambiguity safely)
        prog_name = "Bachelor of Science in Computer Science"
        matching_programs = db.scalars(
            select(Program).where(
                Program.department_id == dept.department_id,
                Program.program_name == prog_name,
            )
        ).all()
        if len(matching_programs) > 1:
            raise ValueError(
                f"Ambiguous seed match: multiple programs found with name '{prog_name}' "
                f"in department ID {dept.department_id}."
            )
        program = matching_programs[0] if matching_programs else None

        if not program:
            program = Program(
                department_id=dept.department_id,
                program_name=prog_name,
                degree_level="Undergraduate",
            )
            db.add(program)
            db.flush()
            record_stat("programs", created=True)
        else:
            record_stat("programs", created=False)

        # Courses (DB Unique: uq_courses_course_code)
        courses_spec = [
            {
                "code": "CS-301",
                "title": "Software Engineering",
                "credit_hours": Decimal("3.0"),
            },
            {
                "code": "CS-302",
                "title": "Database Systems",
                "credit_hours": Decimal("4.0"),
            },
        ]
        courses_by_code: Dict[str, Course] = {}
        for c_spec in courses_spec:
            course = db.scalar(
                select(Course).where(Course.course_code == c_spec["code"])
            )
            if not course:
                course = Course(
                    department_id=dept.department_id,
                    course_code=c_spec["code"],
                    course_title=c_spec["title"],
                    credit_hours=c_spec["credit_hours"],
                )
                db.add(course)
                db.flush()
                record_stat("courses", created=True)
            else:
                record_stat("courses", created=False)
            courses_by_code[c_spec["code"]] = course

        # Semester (DB Unique: uq_semesters_name_year)
        semester = db.scalar(
            select(Semester).where(
                Semester.semester_name == "Spring 2026",
                Semester.academic_year == "2025-2026",
            )
        )
        if not semester:
            semester = Semester(
                semester_name="Spring 2026",
                academic_year="2025-2026",
                start_date=date(2026, 2, 1),
                end_date=date(2026, 6, 30),
            )
            db.add(semester)
            db.flush()
            record_stat("semesters", created=True)
        else:
            record_stat("semesters", created=False)

        # =====================================================================
        # 4. CONFIGURABLE DEMONSTRATION GRADING SCHEME & GRADE BANDS
        # Designated as synthetic demonstration scheme.
        # =====================================================================
        demo_scheme_name = "Demo Standard Letter Grading Scheme"
        matching_schemes = db.scalars(
            select(GradingScheme).where(
                GradingScheme.scheme_name == demo_scheme_name
            )
        ).all()
        if len(matching_schemes) > 1:
            raise ValueError(
                f"Ambiguous seed match: multiple grading schemes found with name '{demo_scheme_name}'."
            )
        grading_scheme = matching_schemes[0] if matching_schemes else None

        if not grading_scheme:
            grading_scheme = GradingScheme(
                scheme_name=demo_scheme_name,
                description=(
                    "Synthetic configurable grading scheme for demonstration "
                    "and test calculations. Subject to institutional confirmation."
                ),
                is_active=True,
            )
            db.add(grading_scheme)
            db.flush()
            record_stat("grading_schemes", created=True)
        else:
            record_stat("grading_schemes", created=False)

        # Grade Bands (Identified per grading_scheme_id + letter_grade, detect ambiguity)
        demo_bands = [
            {"letter": "A", "min": Decimal("85.00"), "max": Decimal("100.00"), "pts": Decimal("4.00")},
            {"letter": "B+", "min": Decimal("80.00"), "max": Decimal("84.99"), "pts": Decimal("3.50")},
            {"letter": "B", "min": Decimal("70.00"), "max": Decimal("79.99"), "pts": Decimal("3.00")},
            {"letter": "C", "min": Decimal("60.00"), "max": Decimal("69.99"), "pts": Decimal("2.00")},
            {"letter": "D", "min": Decimal("50.00"), "max": Decimal("59.99"), "pts": Decimal("1.00")},
            {"letter": "F", "min": Decimal("0.00"), "max": Decimal("49.99"), "pts": Decimal("0.00")},
        ]
        for band_spec in demo_bands:
            matching_bands = db.scalars(
                select(GradeBand).where(
                    GradeBand.grading_scheme_id == grading_scheme.grading_scheme_id,
                    GradeBand.letter_grade == band_spec["letter"],
                )
            ).all()
            if len(matching_bands) > 1:
                raise ValueError(
                    f"Ambiguous seed match: multiple grade bands found with letter grade '{band_spec['letter']}' "
                    f"in grading scheme ID {grading_scheme.grading_scheme_id}."
                )
            band = matching_bands[0] if matching_bands else None

            if not band:
                band = GradeBand(
                    grading_scheme_id=grading_scheme.grading_scheme_id,
                    minimum_marks=band_spec["min"],
                    maximum_marks=band_spec["max"],
                    letter_grade=band_spec["letter"],
                    grade_points=band_spec["pts"],
                )
                db.add(band)
                db.flush()
                record_stat("grade_bands", created=True)
            else:
                record_stat("grade_bands", created=False)

        # =====================================================================
        # 5. FACULTY & STUDENT PROFILES
        # Resolve employee_number/registration_number and user_id independently.
        # Detect conflicting identities.
        # =====================================================================
        # Faculty (DB Unique: uq_faculty_employee_number, uq_faculty_user_id)
        faculty_user = users_by_username["faculty_demo"]
        fac_by_emp = db.scalar(
            select(Faculty).where(Faculty.employee_number == "EMP-CS-001")
        )
        fac_by_user = db.scalar(
            select(Faculty).where(Faculty.user_id == faculty_user.user_id)
        )
        if (
            fac_by_emp is not None
            and fac_by_user is not None
            and fac_by_emp.faculty_id != fac_by_user.faculty_id
        ):
            raise ValueError(
                f"Faculty identity conflict: employee number 'EMP-CS-001' belongs to faculty ID "
                f"{fac_by_emp.faculty_id}, while user ID {faculty_user.user_id} belongs to distinct "
                f"faculty ID {fac_by_user.faculty_id}. Aborting seed."
            )
        faculty = fac_by_emp or fac_by_user

        if not faculty:
            faculty = Faculty(
                user_id=faculty_user.user_id,
                employee_number="EMP-CS-001",
                department_id=dept.department_id,
                designation="Assistant Professor",
            )
            db.add(faculty)
            db.flush()
            record_stat("faculty", created=True)
        else:
            record_stat("faculty", created=False)

        # Students (DB Unique: uq_students_registration_number, uq_students_user_id)
        student_specs = [
            ("student1_demo", "2022-CS-001"),
            ("student2_demo", "2022-CS-002"),
        ]
        students_by_reg: Dict[str, Student] = {}
        for u_key, reg_num in student_specs:
            st_user = users_by_username[u_key]
            st_by_reg = db.scalar(
                select(Student).where(Student.registration_number == reg_num)
            )
            st_by_user = db.scalar(
                select(Student).where(Student.user_id == st_user.user_id)
            )
            if (
                st_by_reg is not None
                and st_by_user is not None
                and st_by_reg.student_id != st_by_user.student_id
            ):
                raise ValueError(
                    f"Student identity conflict: registration number '{reg_num}' belongs to student ID "
                    f"{st_by_reg.student_id}, while user ID {st_user.user_id} belongs to distinct "
                    f"student ID {st_by_user.student_id}. Aborting seed."
                )
            student = st_by_reg or st_by_user

            if not student:
                student = Student(
                    user_id=st_user.user_id,
                    registration_number=reg_num,
                    program_id=program.program_id,
                    current_semester_number=6,
                )
                db.add(student)
                db.flush()
                record_stat("students", created=True)
            else:
                record_stat("students", created=False)
            students_by_reg[reg_num] = student

        student1 = students_by_reg["2022-CS-001"]
        student2 = students_by_reg["2022-CS-002"]

        # =====================================================================
        # 6. COURSE OFFERINGS & FACULTY ASSIGNMENTS
        # DB Unique: uq_course_offerings_course_semester_section
        # =====================================================================
        # Offering 1: CS-301, Spring 2026, Section A
        offering1 = db.scalar(
            select(CourseOffering).where(
                CourseOffering.course_id == courses_by_code["CS-301"].course_id,
                CourseOffering.semester_id == semester.semester_id,
                CourseOffering.section_code == "A",
            )
        )
        if not offering1:
            offering1 = CourseOffering(
                course_id=courses_by_code["CS-301"].course_id,
                semester_id=semester.semester_id,
                grading_scheme_id=grading_scheme.grading_scheme_id,
                section_code="A",
                seat_capacity=40,
                status="OPEN",
            )
            db.add(offering1)
            db.flush()
            record_stat("course_offerings", created=True)
        else:
            record_stat("course_offerings", created=False)

        # Offering 2: CS-302, Spring 2026, Section A
        offering2 = db.scalar(
            select(CourseOffering).where(
                CourseOffering.course_id == courses_by_code["CS-302"].course_id,
                CourseOffering.semester_id == semester.semester_id,
                CourseOffering.section_code == "A",
            )
        )
        if not offering2:
            offering2 = CourseOffering(
                course_id=courses_by_code["CS-302"].course_id,
                semester_id=semester.semester_id,
                grading_scheme_id=grading_scheme.grading_scheme_id,
                section_code="A",
                seat_capacity=35,
                status="OPEN",
            )
            db.add(offering2)
            db.flush()
            record_stat("course_offerings", created=True)
        else:
            record_stat("course_offerings", created=False)

        # Faculty Assignments (DB Unique: uq_faculty_assignments_offering_faculty)
        for off in [offering1, offering2]:
            assignment = db.scalar(
                select(FacultyAssignment).where(
                    FacultyAssignment.offering_id == off.offering_id,
                    FacultyAssignment.faculty_id == faculty.faculty_id,
                )
            )
            if not assignment:
                assignment = FacultyAssignment(
                    offering_id=off.offering_id,
                    faculty_id=faculty.faculty_id,
                )
                db.add(assignment)
                db.flush()
                record_stat("faculty_assignments", created=True)
            else:
                record_stat("faculty_assignments", created=False)

        # =====================================================================
        # 7. REGISTRATIONS (DB Unique: uq_registrations_student_offering)
        # =====================================================================
        # Student 1 in Offering 1
        reg_s1_o1 = db.scalar(
            select(Registration).where(
                Registration.student_id == student1.student_id,
                Registration.offering_id == offering1.offering_id,
            )
        )
        if not reg_s1_o1:
            reg_s1_o1 = Registration(
                student_id=student1.student_id,
                offering_id=offering1.offering_id,
                registration_date=date(2026, 2, 5),
                registration_status="REGISTERED",
            )
            db.add(reg_s1_o1)
            db.flush()
            record_stat("registrations", created=True)
        else:
            record_stat("registrations", created=False)

        # Student 1 in Offering 2
        reg_s1_o2 = db.scalar(
            select(Registration).where(
                Registration.student_id == student1.student_id,
                Registration.offering_id == offering2.offering_id,
            )
        )
        if not reg_s1_o2:
            reg_s1_o2 = Registration(
                student_id=student1.student_id,
                offering_id=offering2.offering_id,
                registration_date=date(2026, 2, 5),
                registration_status="REGISTERED",
            )
            db.add(reg_s1_o2)
            db.flush()
            record_stat("registrations", created=True)
        else:
            record_stat("registrations", created=False)

        # Student 2 in Offering 1
        reg_s2_o1 = db.scalar(
            select(Registration).where(
                Registration.student_id == student2.student_id,
                Registration.offering_id == offering1.offering_id,
            )
        )
        if not reg_s2_o1:
            reg_s2_o1 = Registration(
                student_id=student2.student_id,
                offering_id=offering1.offering_id,
                registration_date=date(2026, 2, 5),
                registration_status="REGISTERED",
            )
            db.add(reg_s2_o1)
            db.flush()
            record_stat("registrations", created=True)
        else:
            record_stat("registrations", created=False)

        # =====================================================================
        # 8. ASSESSMENTS & RESULTS
        # =====================================================================
        # Assessment (No DB uniqueness constraint -> detect ambiguity safely)
        midterm_title = "Midterm Examination"
        matching_assessments = db.scalars(
            select(Assessment).where(
                Assessment.offering_id == offering1.offering_id,
                Assessment.assessment_name == midterm_title,
            )
        ).all()
        if len(matching_assessments) > 1:
            raise ValueError(
                f"Ambiguous seed match: multiple assessments found with name '{midterm_title}' "
                f"in course offering ID {offering1.offering_id}."
            )
        assessment = matching_assessments[0] if matching_assessments else None

        if not assessment:
            assessment = Assessment(
                offering_id=offering1.offering_id,
                assessment_name=midterm_title,
                assessment_type="Midterm",
                maximum_marks=Decimal("30.00"),
                weightage=Decimal("30.00"),
            )
            db.add(assessment)
            db.flush()
            record_stat("assessments", created=True)
        else:
            record_stat("assessments", created=False)

        # Assessment Result (DB Unique: uq_assessment_results_assessment_registration)
        result = db.scalar(
            select(AssessmentResult).where(
                AssessmentResult.assessment_id == assessment.assessment_id,
                AssessmentResult.registration_id == reg_s1_o1.registration_id,
            )
        )
        if not result:
            result = AssessmentResult(
                assessment_id=assessment.assessment_id,
                registration_id=reg_s1_o1.registration_id,
                obtained_marks=Decimal("26.50"),
            )
            db.add(result)
            db.flush()
            record_stat("assessment_results", created=True)
        else:
            record_stat("assessment_results", created=False)

        # =====================================================================
        # 9. ATTENDANCE SESSIONS
        # (Note: AttendanceRecord creation is deferred until institutional attendance
        # statuses are formally approved. Only the dated class session topic is seeded.)
        # =====================================================================
        session_date = date(2026, 2, 15)
        session_topic = "System Architecture and Modular Backend Design"
        matching_sessions = db.scalars(
            select(AttendanceSession).where(
                AttendanceSession.offering_id == offering1.offering_id,
                AttendanceSession.session_date == session_date,
                AttendanceSession.topic == session_topic,
            )
        ).all()
        if len(matching_sessions) > 1:
            raise ValueError(
                f"Ambiguous seed match: multiple attendance sessions found matching offering ID "
                f"{offering1.offering_id}, date {session_date}, and topic '{session_topic}'."
            )
        att_session = matching_sessions[0] if matching_sessions else None

        if not att_session:
            att_session = AttendanceSession(
                offering_id=offering1.offering_id,
                session_date=session_date,
                topic=session_topic,
            )
            db.add(att_session)
            db.flush()
            record_stat("attendance_sessions", created=True)
        else:
            record_stat("attendance_sessions", created=False)

        # =====================================================================
        # 10. SYNTHETIC FEE RECORDS & MANUAL PAYMENTS
        # =====================================================================
        finance_user = users_by_username["finance_demo"]

        # Fee Record (No DB uniqueness constraint -> detect ambiguity safely)
        fee_desc = "Semester Tuition Fee - Spring 2026"
        matching_fee_records = db.scalars(
            select(FeeRecord).where(
                FeeRecord.student_id == student1.student_id,
                FeeRecord.fee_description == fee_desc,
            )
        ).all()
        if len(matching_fee_records) > 1:
            raise ValueError(
                f"Ambiguous seed match: multiple fee records found for student ID {student1.student_id} "
                f"with description '{fee_desc}'."
            )
        fee_record = matching_fee_records[0] if matching_fee_records else None

        if not fee_record:
            fee_record = FeeRecord(
                student_id=student1.student_id,
                fee_description=fee_desc,
                total_charges=Decimal("75000.00"),
                due_date=date(2026, 2, 28),
                created_by_user_id=finance_user.user_id,
            )
            db.add(fee_record)
            db.flush()
            record_stat("fee_records", created=True)
        else:
            record_stat("fee_records", created=False)

        # Fee Payment Record (No DB uniqueness constraint -> detect ambiguity safely)
        ref_num = "DEMO-MANUAL-REC-001"
        matching_payments = db.scalars(
            select(FeePaymentRecord).where(
                FeePaymentRecord.fee_record_id == fee_record.fee_record_id,
                FeePaymentRecord.reference_number == ref_num,
            )
        ).all()
        if len(matching_payments) > 1:
            raise ValueError(
                f"Ambiguous seed match: multiple fee payment records found with reference '{ref_num}' "
                f"for fee record ID {fee_record.fee_record_id}."
            )
        payment_record = matching_payments[0] if matching_payments else None

        if not payment_record:
            payment_record = FeePaymentRecord(
                fee_record_id=fee_record.fee_record_id,
                recorded_by_user_id=finance_user.user_id,
                amount_paid=Decimal("75000.00"),
                payment_date=date(2026, 2, 20),
                reference_number=ref_num,
            )
            db.add(payment_record)
            db.flush()
            record_stat("fee_payment_records", created=True)
        else:
            record_stat("fee_payment_records", created=False)

    return stats
