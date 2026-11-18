import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.domain.staff_access import ROLE_ADMIN, ROLE_MANAGER, ROLE_TEACHER, can_access_resource
from app.models import Course, Lead
from app.repositories import course_has_references


ROOT = Path(__file__).resolve().parents[1]


class InterestActivityAdminTest(unittest.TestCase):
    def test_only_platform_admin_can_manage_interest_activities(self):
        self.assertTrue(can_access_resource(ROLE_ADMIN, "courses"))
        self.assertFalse(can_access_resource(ROLE_MANAGER, "courses"))
        self.assertFalse(can_access_resource(ROLE_TEACHER, "courses"))

        navigation = (ROOT / "app/templates/_nav.html").read_text(encoding="utf-8")
        self.assertIn('href="/admin/courses"', navigation)
        self.assertIn("兴趣活动", navigation)

    def test_referenced_activity_is_protected_from_deletion(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            course = Course(id="activity", title="绘画", category="绘画")
            db.add(course)
            db.flush()
            db.add(Lead(name="家长", phone="13800138000", child_grade="小学", source="course", course_id=course.id))
            db.commit()

            self.assertTrue(course_has_references(db, course.id))
            self.assertFalse(course_has_references(db, "unused"))


if __name__ == "__main__":
    unittest.main()
