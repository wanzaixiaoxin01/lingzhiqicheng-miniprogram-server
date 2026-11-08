import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.db import Base
from app.repositories import list_published_materials


class MaterialRepositoryTest(unittest.TestCase):
    def test_published_materials_are_newest_first_regardless_of_legacy_sort_order(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            older = models.Material(
                id="older-material",
                title="较早资料",
                original_name="older.pdf",
                storage_name="older.pdf",
                extension=".pdf",
                content_type="application/pdf",
                file_size=10,
                can_preview=True,
                sort_order=1,
                status="published",
                created_at=datetime(2026, 1, 1),
            )
            newer = models.Material(
                id="newer-material",
                title="最新资料",
                original_name="newer.pdf",
                storage_name="newer.pdf",
                extension=".pdf",
                content_type="application/pdf",
                file_size=10,
                can_preview=True,
                sort_order=999,
                status="published",
                created_at=datetime(2026, 1, 2),
            )
            db.add_all([older, newer])
            db.commit()

            self.assertEqual([item.id for item in list_published_materials(db)], ["newer-material", "older-material"])


if __name__ == "__main__":
    unittest.main()
