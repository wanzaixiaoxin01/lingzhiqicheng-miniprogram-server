import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi import Request

from app import models, repositories
from app.db import Base
from app.routes.admin_pages import list_resource, update_lead_status


class LeadAdminRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add_all([
            models.Campus(id="campus-a", name="A网点", address="A", phone="13800138000"),
            models.Campus(id="campus-b", name="B网点", address="B", phone="13800138001"),
        ])
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
                    child_name="小明",
                    phone=phone,
                    campus_id="campus-a" if index % 2 == 0 else "campus-b",
                    child_age=10,
                    child_grade="小学四年级",
                    appointment_at=datetime(2026, 11, 20, 14, 30, tzinfo=timezone.utc),
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

    def test_filters_leads_by_campus(self):
        result = repositories.list_admin_leads(self.db, campus_id="campus-b")

        self.assertEqual(result.total, 2)
        self.assertTrue(all(lead.campus_id == "campus-b" for lead in result.items))

    def test_scoped_leads_only_include_allowed_campuses(self):
        result = repositories.list_admin_leads(self.db, campus_ids=["campus-a"])
        self.assertEqual(result.total, 3)
        self.assertTrue(all(lead.campus_id == "campus-a" for lead in result.items))

    def render_leads(self, **filters):
        request = Request({"type": "http", "method": "GET", "path": "/admin/leads", "headers": [], "query_string": b""})
        return list_resource("leads", request, db=self.db, **filters)

    def test_tabs_default_to_pending_and_show_all_status_totals(self):
        response = self.render_leads()
        self.assertEqual(response.context["filters"]["follow_status"], "pending")
        self.assertEqual(response.context["pagination"].total, 3)
        self.assertEqual(response.context["lead_status_counts"], {"pending": 3, "contacted": 1, "converted": 1})
        html = response.body.decode()
        self.assertEqual(html.count('class="lead-status-tab '), 7)
        self.assertIn('lead-status-count is-pending', html)
        self.assertIn('aria-current="page"', html)
        self.assertIn('name="follow_status" value="pending"', html)
        self.assertNotIn("王小明爸爸", html)

    def test_empty_child_fields_render_as_unknown(self):
        self.db.add(models.Lead(
            id="lead-empty", name="家长", child_name=None, child_age=None,
            child_grade=None, child_school=None, phone="13800000000",
            campus_id="campus-a", source="trial", follow_status="pending",
            appointment_at=datetime(2026, 11, 20, 14, 30, tzinfo=timezone.utc),
        ))
        self.db.commit()
        html = self.render_leads().body.decode()
        self.assertIn("未知 · 未知 · 未知", html)
        self.assertIn("当前就读学校：未知", html)

    def test_search_stays_within_tab_and_totals_remain_global(self):
        response = self.render_leads(follow_status="contacted", phone="5678", campus_id="campus-b")
        self.assertEqual([item.id for item in response.context["items"]], ["lead-1"])
        self.assertEqual(response.context["lead_status_counts"]["pending"], 3)
        self.assertIn("follow_status=contacted", response.context["current_url"])
        self.assertIn('href="/admin/leads?follow_status=contacted">重置', response.body.decode())
        self.assertEqual(self.render_leads(follow_status="unknown").context["filters"]["follow_status"], "pending")

    def test_status_update_moves_lead_and_refreshes_counts(self):
        update_lead_status("lead-0", follow_status="visited", follow_note="已到店", return_to="/admin/leads?follow_status=pending", db=self.db)
        response = self.render_leads()
        self.assertEqual(response.context["pagination"].total, 2)
        self.assertEqual(response.context["lead_status_counts"]["visited"], 1)
        visited = self.render_leads(follow_status="visited")
        self.assertEqual([item.id for item in visited.context["items"]], ["lead-0"])

    def test_not_considering_can_be_selected_and_reopened(self):
        update_lead_status("lead-1", follow_status="not_considering", follow_note="家长暂时没有需求", db=self.db, return_to="/admin/leads")
        response = self.render_leads(follow_status="not_considering")
        self.assertEqual([item.id for item in response.context["items"]], ["lead-1"])
        self.assertEqual(response.context["lead_status_counts"]["not_considering"], 1)
        self.assertIn("暂不考虑", response.body.decode())
        self.assertIn("家长暂时没有需求", response.body.decode())
        update_lead_status("lead-1", follow_status="contacted", follow_note="重新联系", db=self.db, return_to="/admin/leads")
        self.assertEqual(self.render_leads(follow_status="not_considering").context["pagination"].total, 0)
        self.assertEqual(self.db.get(models.Lead, "lead-1").follow_status, "contacted")

    def test_zero_pending_has_neutral_count(self):
        for lead in self.db.query(models.Lead).filter_by(follow_status="pending"):
            lead.follow_status = "contacted"
        self.db.commit()
        html = self.render_leads().body.decode()
        self.assertIn('lead-status-count is-empty', html)
        self.assertNotIn('lead-status-count is-pending', html)


if __name__ == "__main__":
    unittest.main()
