import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app import models, repositories
from app.db import Base
from app.domain.leads import validate_lead_input


BEIJING = ZoneInfo("Asia/Shanghai")


class AppointmentConstraintsTest(unittest.TestCase):
    def payload(self, appointment_at="2026-11-23T14:30:00+08:00"):
        return {
            "name": "王女士",
            "child_name": "小明",
            "phone": "13800138000",
            "child_age": 10,
            "child_grade": "四年级",
            "source": "trial",
            "campus_id": "campus-1",
            "appointment_at": appointment_at,
        }

    def test_requires_campus_and_appointment_time(self):
        payload = self.payload()
        payload["campus_id"] = ""
        payload["appointment_at"] = ""

        result = validate_lead_input(payload, now=datetime(2026, 11, 22, 12, 0, tzinfo=BEIJING))

        self.assertEqual(result.errors["campus_id"], "请选择预约网点")
        self.assertEqual(result.errors["appointment_at"], "请选择预约日期")

    def test_requires_future_timezone_aware_appointment_time(self):
        now = datetime(2026, 11, 22, 12, 0, tzinfo=BEIJING)
        past = validate_lead_input(self.payload("2026-11-22T11:59:00+08:00"), now=now)
        naive = validate_lead_input(self.payload("2026-11-23T14:30:00"), now=now)
        future = validate_lead_input(self.payload(), now=now)

        self.assertTrue(past.ok)
        self.assertTrue(naive.ok)
        self.assertTrue(future.ok)
        self.assertEqual(future.value["appointment_at"].isoformat(), "2026-11-23T14:30:00+08:00")

    def test_same_day_appointment_has_no_time_notice_requirement(self):
        for now in [datetime(2026, 11, 22, 12, 0, tzinfo=BEIJING),
                    datetime(2026, 11, 22, 23, 55, 30, tzinfo=BEIJING)]:
            for seconds, accepted in [(0, True), (599, True), (600, True)]:
                with self.subTest(now=now, seconds=seconds):
                    payload = self.payload((now + timedelta(seconds=seconds)).isoformat())
                    result = validate_lead_input(payload, now=now)
                    self.assertEqual(result.ok, accepted)

    def test_lead_columns_store_campus_and_time_as_required_fields(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        columns = {column["name"]: column for column in inspect(engine).get_columns("leads")}

        self.assertFalse(columns["campus_id"]["nullable"])
        self.assertFalse(columns["appointment_at"]["nullable"])
        engine.dispose()

    def test_daily_limit_uses_beijing_calendar_day_and_resets_next_day(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        day_one = datetime(2026, 11, 22, 12, 0, tzinfo=BEIJING)
        with Session(engine) as db:
            user = models.User(id="parent-1", openid="wx-parent-1")
            campus = models.Campus(id="campus-1", name="北舞渡网点", address="地址", phone="13800138000")
            db.add_all([user, campus])
            db.flush()
            for index in range(10):
                db.add(models.Lead(
                    id=f"lead-{index}",
                    user_id=user.id,
                    campus_id=campus.id,
                    name="家长",
                    child_name="小明",
                    phone="13800138000",
                    child_age=10,
                    child_grade="四年级",
                    appointment_at=day_one + timedelta(days=2),
                    source="trial",
                    created_at=day_one + timedelta(minutes=index),
                ))
            db.commit()

            self.assertTrue(repositories.parent_daily_lead_limit_reached(db, user.id, now=day_one))
            self.assertFalse(
                repositories.parent_daily_lead_limit_reached(db, user.id, now=day_one + timedelta(days=1))
            )
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
