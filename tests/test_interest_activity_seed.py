import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Campus, Course
from app.seed import CAMPUS_SEED, INTEREST_ACTIVITY_SEED, seed_campuses, seed_courses


class InterestActivitySeedTest(unittest.TestCase):
    def test_seed_upserts_three_historical_self_study_locations(self):
        with Session(self.engine) as db:
            seed_campuses(db)
            seed_campuses(db)
            db.commit()

            campuses = db.query(Campus).order_by(Campus.id).all()
            self.assertEqual(len(campuses), 3)
            self.assertEqual(
                {campus.name for campus in campuses},
                {"郾城服务点", "莲花服务点", "北舞渡服务点"},
            )
            self.assertTrue(all(campus.address for campus in campuses))
            self.assertTrue(all(campus.phone == "4009006368" for campus in campuses))
            self.assertTrue(all(campus.status == "published" for campus in campuses))

        self.assertEqual(len(CAMPUS_SEED), 3)

    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    def test_seed_upserts_six_current_activities_and_hides_legacy_courses(self):
        with Session(self.engine) as db:
            db.add(Course(id="legacy", title="课后晚托服务", category="晚托", status="published"))
            db.add(Course(id="custom", title="舞蹈体验", category="舞蹈", status="published"))
            db.commit()

            seed_courses(db)
            seed_courses(db)
            db.commit()

            current = db.query(Course).filter(Course.id.in_([item["id"] for item in INTEREST_ACTIVITY_SEED])).all()
            legacy = db.get(Course, "legacy")
            custom = db.get(Course, "custom")

        self.assertEqual(len(INTEREST_ACTIVITY_SEED), 6)
        self.assertEqual(len(current), 6)
        self.assertEqual([item["sort_order"] for item in INTEREST_ACTIVITY_SEED], [1, 2, 3, 4, 5, 6])
        self.assertTrue(all(item.status == "published" for item in current))
        self.assertEqual(legacy.status, "hidden")
        self.assertEqual(custom.status, "published")

    def test_seed_contains_current_activity_names_and_server_covers(self):
        self.assertEqual(
            [item["title"] for item in INTEREST_ACTIVITY_SEED],
            ["编程与逻辑", "英语口语", "表达与阅读", "练字", "绘画", "音乐与乐器"],
        )
        self.assertTrue(all(item["cover_url"].startswith("/static/courses/") for item in INTEREST_ACTIVITY_SEED))


if __name__ == "__main__":
    unittest.main()
