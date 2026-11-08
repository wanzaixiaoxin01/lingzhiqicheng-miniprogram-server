import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import hash_password, verify_password
from app.db import Base
from app.domain.staff_access import ROLE_ADMIN, ROLE_MANAGER, ROLE_TEACHER, can_access_resource, menu_resources
from app.models import AdminUser, AttendanceRecord, Campus, Student, StudentEnrollment, StaffCampus


class OperationsDomainTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(cls.engine)

    def setUp(self):
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_password_hash_round_trip(self):
        hashed = hash_password("teacher-secret")
        self.assertNotEqual(hashed, "teacher-secret")
        self.assertTrue(verify_password("teacher-secret", hashed))
        self.assertFalse(verify_password("wrong", hashed))

    def test_roles_have_different_resource_access(self):
        self.assertTrue(can_access_resource(ROLE_ADMIN, "campuses"))
        self.assertTrue(can_access_resource(ROLE_ADMIN, "staff"))
        self.assertFalse(can_access_resource(ROLE_ADMIN, "courses"))
        self.assertTrue(can_access_resource(ROLE_MANAGER, "students"))
        self.assertTrue(can_access_resource(ROLE_MANAGER, "staff"))
        self.assertTrue(can_access_resource(ROLE_MANAGER, "visits"))
        self.assertFalse(can_access_resource(ROLE_MANAGER, "campuses"))
        self.assertFalse(can_access_resource(ROLE_TEACHER, "staff"))
        self.assertFalse(can_access_resource(ROLE_TEACHER, "enrollments"))
        self.assertFalse(can_access_resource(ROLE_ADMIN, "enrollments"))
        self.assertFalse(can_access_resource(ROLE_MANAGER, "enrollments"))
        self.assertFalse(can_access_resource(ROLE_ADMIN, "settings"))
        self.assertTrue(can_access_resource(ROLE_ADMIN, "banners"))
        self.assertNotIn("courses", menu_resources(ROLE_ADMIN))
        self.assertNotIn("banners", menu_resources(ROLE_ADMIN))
        self.assertNotIn("enrollments", menu_resources(ROLE_ADMIN))
        self.assertNotIn("enrollments", menu_resources(ROLE_MANAGER))
        self.assertNotIn("settings", menu_resources(ROLE_ADMIN))

    def test_student_enrollment_and_attendance_have_service_point_links(self):
        campus = Campus(
            name="莲花服务点",
            address="漯河市郾城区莲花镇",
            phone="13800000000",
            status="published",
        )
        staff = AdminUser(
            username="teacher-lianhua",
            display_name="莲花老师",
            role=ROLE_TEACHER,
            password_hash=hash_password("secret"),
            status="active",
        )
        student = Student(name="张三", grade="小学四年级", guardian_phone="13811112222", status="active")
        self.db.add_all([campus, staff, student])
        self.db.flush()
        self.db.add(StaffCampus(staff_id=staff.id, campus_id=campus.id))
        enrollment = StudentEnrollment(
            student_id=student.id,
            campus_id=campus.id,
            service_type="智习室学习",
            status="active",
        )
        visit = AttendanceRecord(
            student_id=student.id,
            campus_id=campus.id,
            attendance_date=date(2026, 11, 8),
            service_type="智习室学习",
            recorded_by=staff.id,
        )
        self.db.add_all([enrollment, visit])
        self.db.commit()

        self.assertEqual(visit.student_id, student.id)
        self.assertEqual(visit.campus_id, campus.id)
        self.assertEqual(enrollment.campus_id, campus.id)

    def test_duplicate_visit_for_same_student_day_service_is_rejected(self):
        campus = Campus(name="北舞渡服务点", address="漯河市舞阳县北舞渡镇", phone="13800000001")
        student = Student(name="李四", grade="小学五年级", status="active")
        staff = AdminUser(
            username="teacher-beiwudu",
            display_name="北舞渡老师",
            role=ROLE_TEACHER,
            password_hash=hash_password("secret"),
            status="active",
        )
        self.db.add_all([campus, student, staff])
        self.db.flush()
        records = [
            AttendanceRecord(
                student_id=student.id,
                campus_id=campus.id,
                attendance_date=date(2026, 11, 8),
                service_type="英语口语",
                recorded_by=staff.id,
            ),
            AttendanceRecord(
                student_id=student.id,
                campus_id=campus.id,
                attendance_date=date(2026, 11, 8),
                service_type="英语口语",
                recorded_by=staff.id,
            ),
        ]
        self.db.add_all(records)
        with self.assertRaises(IntegrityError):
            self.db.commit()


if __name__ == "__main__":
    unittest.main()
