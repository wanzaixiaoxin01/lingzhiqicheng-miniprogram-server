import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.domain.parent_binding import bind_students_by_verified_phone
from app.models import Student, User


class ParentPhoneBindingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(cls.engine)

    def setUp(self):
        self.db = Session(self.engine)
        self.db.query(Student).delete()
        self.db.query(User).delete()
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_verified_phone_links_every_matching_student(self):
        self.db.add_all([
            Student(name="张小明", grade="七年级", guardian_phone="138 1111 2222"),
            Student(name="张小雨", grade="三年级", guardian_phone="13811112222"),
            Student(name="其他学生", grade="五年级", guardian_phone="13900000000"),
        ])
        self.db.commit()

        result = bind_students_by_verified_phone(self.db, "wx-parent", "138-1111-2222")

        self.assertEqual(result.parent.phone, "13811112222")
        self.assertEqual({item.name for item in result.students}, {"张小明", "张小雨"})
        self.assertTrue(all(item.guardian_user_id == result.parent.id for item in result.students))

    def test_verified_phone_is_saved_when_no_student_matches(self):
        result = bind_students_by_verified_phone(self.db, "wx-parent", "13811112222")

        self.assertEqual(result.parent.phone, "13811112222")
        self.assertEqual(result.students, [])

    def test_existing_other_parent_binding_is_not_overwritten(self):
        other = User(openid="wx-other", phone="13811112222")
        self.db.add(other)
        self.db.flush()
        self.db.add(Student(
            name="张小明",
            grade="七年级",
            guardian_phone="13811112222",
            guardian_user_id=other.id,
        ))
        self.db.commit()

        with self.assertRaisesRegex(ValueError, "已绑定其他微信"):
            bind_students_by_verified_phone(self.db, "wx-parent", "13811112222")


if __name__ == "__main__":
    unittest.main()
