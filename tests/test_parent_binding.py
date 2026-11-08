import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.domain.parent_binding import bind_student_to_parent, list_parent_students
from app.models import Campus, Student, StudentEnrollment, User


class ParentBindingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(cls.engine)

    def setUp(self):
        self.db = Session(self.engine)
        self.db.query(StudentEnrollment).delete()
        self.db.query(Student).delete()
        self.db.query(Campus).delete()
        self.db.query(User).delete()
        self.db.commit()
        campus = Campus(name="莲花服务点", address="漯河", phone="13800000000")
        student = Student(
            name="张三",
            grade="小学四年级",
            guardian_phone="13811112222",
            binding_code="ABCD1234",
            binding_code_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        self.db.add_all([campus, student])
        self.db.flush()
        self.db.add(
            StudentEnrollment(
                student_id=student.id,
                campus_id=campus.id,
                service_type="智习室学习",
                status="active",
            )
        )
        self.db.commit()
        self.student = student

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_bind_requires_matching_guardian_phone_and_consumes_code(self):
        with self.assertRaises(ValueError):
            bind_student_to_parent(self.db, "ABCD1234", "wx-parent", "13800000000")

        parent = bind_student_to_parent(self.db, "ABCD1234", "wx-parent", "13811112222")

        self.assertEqual(parent.openid, "wx-parent")
        self.assertEqual(self.student.guardian_user_id, parent.id)
        self.assertIsNone(self.student.binding_code)
        self.assertEqual([item.name for item in list_parent_students(self.db, parent.id)], ["张三"])

    def test_expired_code_is_rejected(self):
        self.student.binding_code_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.db.commit()

        with self.assertRaises(ValueError):
            bind_student_to_parent(self.db, "ABCD1234", "wx-parent", "13811112222")

    def test_same_parent_can_bind_multiple_students(self):
        parent = bind_student_to_parent(self.db, "ABCD1234", "wx-parent", "13811112222")
        second = Student(
            name="李四",
            grade="小学五年级",
            guardian_phone="13811112222",
            binding_code="EFGH5678",
            binding_code_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        self.db.add(second)
        self.db.commit()

        bind_student_to_parent(self.db, "EFGH5678", "wx-parent", "13811112222")

        self.assertEqual({item.name for item in list_parent_students(self.db, parent.id)}, {"张三", "李四"})

    def test_existing_binding_cannot_be_taken_by_another_parent(self):
        bind_student_to_parent(self.db, "ABCD1234", "wx-parent", "13811112222")
        self.student.binding_code = "REISSUED1"
        self.student.binding_code_expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        self.db.commit()

        with self.assertRaises(ValueError):
            bind_student_to_parent(self.db, "REISSUED1", "another-parent", "13811112222")


if __name__ == "__main__":
    unittest.main()
