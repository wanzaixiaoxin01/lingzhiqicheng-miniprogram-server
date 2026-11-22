import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.db import Base
from app.domain.leads import validate_lead_input
from app.models import Campus, Lead, User
from app.routes.public_api import create_lead, get_parent_appointments
from test_parent_api import parent_request


class LeadAgeTest(unittest.TestCase):
    def payload(self, age):
        appointment_at = datetime.now(ZoneInfo("Asia/Shanghai")) + timedelta(days=1)
        return dict(
            name="家长",
            child_name="小明",
            phone="13800138000",
            child_grade="四年级",
            child_age=age,
            source="trial",
            campus_id="campus-1",
            appointment_at=appointment_at.isoformat(),
        )

    def test_valid_age_is_saved_and_returned_in_history(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([User(openid="wx-parent"), Campus(id="campus-1", name="北舞渡网点", address="地址", phone="13800138000")])
            db.commit()
            created = create_lead(self.payload(10), parent_request("wx-parent"), db)
            self.assertEqual(db.get(Lead, created.id).child_age, 10)
            self.assertEqual(created.child_age, 10)
            self.assertEqual(get_parent_appointments(parent_request("wx-parent"), db)[0].child_age, 10)
        engine.dispose()

    def test_age_bounds_and_invalid_values(self):
        for age in [1, 30]:
            with self.subTest(age=age):
                result = validate_lead_input(self.payload(age))
                self.assertTrue(result.ok)
                self.assertEqual(result.value["child_age"], age)
        for age in [0, 31, -1, 5.5, True, "five"]:
            with self.subTest(age=age):
                result = validate_lead_input(self.payload(age))
                self.assertFalse(result.ok)
                self.assertIn("child_age", result.errors)

    def test_missing_age_is_optional(self):
        payload = self.payload(10)
        del payload["child_age"]
        result = validate_lead_input(payload)

        self.assertTrue(result.ok)
        self.assertIsNone(result.value["child_age"])

    def test_new_lead_table_allows_missing_age(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        child_age = next(
            column for column in inspect(engine).get_columns("leads")
            if column["name"] == "child_age"
        )
        self.assertTrue(child_age["nullable"])
        engine.dispose()
