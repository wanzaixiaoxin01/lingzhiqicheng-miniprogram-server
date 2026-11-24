import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.domain.parent_dashboard import build_parent_dashboard
from app.models import AttendanceRecord, Campus, Course, Student, StudentEnrollment, User


class ParentDashboardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(cls.engine)

    def setUp(self):
        self.db = Session(self.engine)
        for model in [AttendanceRecord, StudentEnrollment, Student, User, Course, Campus]:
            self.db.query(model).delete()
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_dashboard_contains_only_current_parents_children_and_newest_records_first(self):
        parent = User(openid="wx-parent", phone="13811112222")
        other_parent = User(openid="wx-other", phone="13900000000")
        campus = Campus(name="莲花服务点", address="漯河", phone="4009006368")
        course = Course(title="AI编程", category="兴趣成长", status="published")
        self.db.add_all([parent, other_parent, campus, course])
        self.db.flush()
        child = Student(name="张小明", grade="七年级", guardian_user_id=parent.id, status="active")
        hidden = Student(name="其他孩子", grade="五年级", guardian_user_id=other_parent.id, status="active")
        self.db.add_all([child, hidden])
        self.db.flush()
        self.db.add(StudentEnrollment(
            student_id=child.id,
            campus_id=campus.id,
            course_id=course.id,
            service_type="智习室学习",
            status="active",
            started_on=date(2026, 1, 1),
            ended_on=date(2026, 12, 31),
        ))
        self.db.add_all([
            AttendanceRecord(
                student_id=child.id,
                campus_id=campus.id,
                course_id=course.id,
                attendance_date=date(2026, 11, 10),
                service_type="智习室学习",
                note="完成数学复习",
                morning_present=True,
                afternoon_present=False,
            ),
            AttendanceRecord(
                student_id=child.id,
                campus_id=campus.id,
                course_id=course.id,
                attendance_date=date(2026, 11, 15),
                service_type="智习室学习",
                morning_present=True,
                afternoon_present=True,
            ),
        ])
        self.db.commit()

        result = build_parent_dashboard(self.db, parent)

        self.assertEqual(result["phone_masked"], "138****2222")
        self.assertFalse(result["needs_phone_authorization"])
        self.assertEqual([item["name"] for item in result["students"]], ["张小明"])
        student = result["students"][0]
        self.assertEqual(student["attendance_count"], 2)
        self.assertEqual(student["enrollments"][0]["campus_name"], "莲花服务点")
        self.assertEqual(student["enrollments"][0]["course_title"], "AI编程")
        self.assertEqual(
            [item["attendance_date"] for item in student["attendance_records"]],
            ["2026-11-15", "2026-11-10"],
        )
        self.assertEqual(
            [item["attendance_period_label"] for item in student["attendance_records"]],
            ["全天", "上午"],
        )
        self.assertTrue(student["attendance_records"][0]["morning_present"])
        self.assertTrue(student["attendance_records"][0]["afternoon_present"])
        self.assertFalse(student["attendance_records"][1]["afternoon_present"])

    def test_dashboard_without_verified_phone_requests_authorization(self):
        parent = User(openid="wx-parent")
        self.db.add(parent)
        self.db.commit()

        result = build_parent_dashboard(self.db, parent)

        self.assertTrue(result["needs_phone_authorization"])
        self.assertEqual(result["students"], [])

    def test_dashboard_picks_up_a_child_registered_after_phone_authorization(self):
        parent = User(openid="wx-parent", phone="13811112222")
        child = Student(
            name="后来报名的孩子",
            grade="三年级",
            guardian_phone="138 1111 2222",
            status="active",
        )
        self.db.add_all([parent, child])
        self.db.commit()

        result = build_parent_dashboard(self.db, parent)

        self.assertEqual([item["name"] for item in result["students"]], ["后来报名的孩子"])
        self.assertEqual(child.guardian_user_id, parent.id)


if __name__ == "__main__":
    unittest.main()
