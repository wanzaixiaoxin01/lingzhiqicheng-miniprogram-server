import unittest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models, repositories
from app.db import Base


class LeadAdminRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        base_time = datetime(2026, 11, 15, 10, 0)
        leads = [
            ("王小明妈妈", "13800138000", "pending"),
            ("王小明爸爸", "13912345678", "contacted"),
            ("李女士", "18600003800", "pending"),
            ("赵先生", "17799990000", "converted"),
            ("陈女士", "13588885678", "pending"),
        ]
        for index, (name, phone, status) in enumerate(leads):
            self.db.add(
                models.Lead(
                    id=f"lead-{index}",
                    name=name,
                    phone=phone,
                    child_grade="小学四年级",
                    source="trial",
                    follow_status=status,
                    created_at=base_time + timedelta(minutes=index),
                )
            )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_filters_name_fuzzily_phone_by_last_four_and_status(self):
        by_name = repositories.list_admin_leads(self.db, parent_name="小明")
        self.assertEqual(by_name.total, 2)

        by_phone = repositories.list_admin_leads(self.db, phone="5678")
        self.assertEqual({lead.phone for lead in by_phone.items}, {"13912345678", "13588885678"})

        by_status = repositories.list_admin_leads(self.db, follow_status="pending")
        self.assertEqual(by_status.total, 3)
        self.assertTrue(all(lead.follow_status == "pending" for lead in by_status.items))

    def test_paginates_results_and_keeps_newest_first(self):
        first_page = repositories.list_admin_leads(self.db, page=1, page_size=2)
        second_page = repositories.list_admin_leads(self.db, page=2, page_size=2)

        self.assertEqual((first_page.total, first_page.total_pages), (5, 3))
        self.assertEqual([lead.id for lead in first_page.items], ["lead-4", "lead-3"])
        self.assertEqual([lead.id for lead in second_page.items], ["lead-2", "lead-1"])

    def test_dashboard_returns_only_latest_pending_leads(self):
        items = repositories.list_latest_pending_leads(self.db, limit=2)
        self.assertEqual([lead.id for lead in items], ["lead-4", "lead-2"])


if __name__ == "__main__":
    unittest.main()
