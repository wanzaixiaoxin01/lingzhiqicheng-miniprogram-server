import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth import parent_session_token
from app.db import Base
from app.models import Campus, Lead, Student, User
from app.routes.public_api import (
    authorize_parent_phone,
    cancel_parent_appointment,
    create_lead,
    get_parent_appointments,
    get_parent_dashboard,
)


def parent_request(openid: str | None = None) -> Request:
    headers = []
    if openid:
        headers.append((b"authorization", f"Bearer {parent_session_token(openid)}".encode()))
    return Request({"type": "http", "headers": headers, "method": "GET", "path": "/"})


def appointment_payload(name: str = "王女士") -> dict:
    appointment_at = datetime.now(ZoneInfo("Asia/Shanghai")) + timedelta(days=1)
    return {
        "name": name,
        "child_name": " 小明 ",
        "phone": "13800138000",
        "child_age": 10,
        "child_grade": "四年级",
        "source": "trial",
        "campus_id": "campus-1",
        "appointment_at": appointment_at.isoformat(),
    }


class ParentApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(cls.engine)

    def setUp(self):
        self.db = Session(self.engine)
        self.db.query(Student).delete()
        self.db.query(Lead).delete()
        self.db.query(User).delete()
        self.db.query(Campus).delete()
        self.db.add(Campus(id="campus-1", name="中心网点", address="测试地址", phone="13800138000"))
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_phone_endpoint_uses_wechat_verified_number_and_links_students(self):
        parent = User(openid="wx-parent")
        lead = Lead(
            campus_id="campus-1",
            name="历史预约家长",
            child_name="小明",
            phone="13811112222",
            child_age=13,
            child_grade="七年级",
            appointment_at=datetime.now(ZoneInfo("Asia/Shanghai")) + timedelta(days=1),
            source="trial",
        )
        self.db.add_all([
            parent,
            Student(name="张小明", grade="七年级", guardian_phone="13811112222"),
            lead,
        ])
        self.db.commit()

        with patch("app.routes.public_api.exchange_phone_code", return_value="13811112222"):
            result = authorize_parent_phone(
                {"code": "wechat-phone-code", "phone": "13900000000"},
                parent_request("wx-parent"),
                self.db,
            )

        self.assertEqual(result.phone_masked, "138****2222")
        self.assertEqual(result.matched_students, 1)
        self.db.refresh(lead)
        self.assertEqual(lead.user_id, parent.id)

    def test_dashboard_rejects_missing_parent_session(self):
        with self.assertRaises(HTTPException) as raised:
            get_parent_dashboard(parent_request(), self.db)

        self.assertEqual(raised.exception.status_code, 401)

    def test_appointment_submission_is_linked_to_wechat_parent(self):
        parent = User(openid="wx-parent")
        self.db.add(parent)
        self.db.commit()

        created = create_lead(
            {**appointment_payload(), "child_school": " 实验小学 "},
            parent_request("wx-parent"),
            self.db,
        )

        lead = self.db.get(Lead, created.id)
        self.assertEqual(lead.user_id, parent.id)
        self.assertEqual(lead.child_name, "小明")
        self.assertEqual(created.child_name, "小明")
        self.assertEqual(lead.child_school, "实验小学")
        self.assertEqual(created.child_school, "实验小学")
        self.assertEqual(get_parent_appointments(parent_request("wx-parent"), self.db)[0].child_school, "实验小学")
        self.assertEqual(get_parent_appointments(parent_request("wx-parent"), self.db)[0].child_name, "小明")

    def test_today_without_child_information_is_saved_and_returned(self):
        self.db.add(User(openid="wx-parent"))
        self.db.commit()
        payload = appointment_payload()
        for field in ("child_name", "child_age", "child_grade", "child_school"):
            payload.pop(field, None)
        payload["appointment_at"] = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
        created = create_lead(payload, parent_request("wx-parent"), self.db)
        lead = self.db.get(Lead, created.id)
        history = get_parent_appointments(parent_request("wx-parent"), self.db)[0]
        for record in (created, lead, history):
            for field in ("child_name", "child_age", "child_grade", "child_school"):
                self.assertIsNone(getattr(record, field))
        self.assertEqual(lead.appointment_at.date().isoformat(), payload["appointment_at"])

    def test_appointment_rejects_missing_or_hidden_campus(self):
        self.db.add(User(openid="wx-parent"))
        self.db.commit()
        missing = appointment_payload()
        missing["campus_id"] = "missing-campus"

        with self.assertRaises(HTTPException) as missing_error:
            create_lead(missing, parent_request("wx-parent"), self.db)

        campus = self.db.get(Campus, "campus-1")
        campus.status = "hidden"
        self.db.commit()
        with self.assertRaises(HTTPException) as hidden_error:
            create_lead(appointment_payload(), parent_request("wx-parent"), self.db)

        self.assertEqual(missing_error.exception.status_code, 400)
        self.assertEqual(hidden_error.exception.status_code, 400)
        self.assertEqual(missing_error.exception.detail["fields"]["campus_id"], "预约网点不存在或不可预约")

    def test_history_uses_current_campus_manager_phone(self):
        self.db.add(User(openid="wx-parent"))
        campus = self.db.get(Campus, "campus-1")
        campus.phone = "13811112222"
        self.db.commit()
        create_lead(appointment_payload(), parent_request("wx-parent"), self.db)
        history = get_parent_appointments(parent_request("wx-parent"), self.db)
        self.assertEqual(history[0].campus_phone, "13811112222")
        self.assertEqual(history[0].phone, "13800138000")
        campus.phone = "13833334444"
        self.db.commit()
        self.assertEqual(get_parent_appointments(parent_request("wx-parent"), self.db)[0].campus_phone, "13833334444")
        campus.phone = ""
        self.db.commit()
        self.assertEqual(get_parent_appointments(parent_request("wx-parent"), self.db)[0].campus_phone, "")

    def test_history_displays_not_considering_label(self):
        self.db.add(User(openid="wx-parent"))
        self.db.commit()
        created = create_lead(appointment_payload(), parent_request("wx-parent"), self.db)
        lead = self.db.get(Lead, created.id)
        lead.follow_status = "not_considering"
        self.db.commit()
        history = get_parent_appointments(parent_request("wx-parent"), self.db)
        self.assertEqual(history[0].follow_status_label, "暂不考虑")

    def test_appointment_submission_requires_wechat_parent(self):
        with self.assertRaises(HTTPException) as raised:
            create_lead(appointment_payload(), parent_request(), self.db)

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(self.db.query(Lead).count(), 0)

    def test_parent_can_submit_ten_appointments_but_not_eleven(self):
        parent = User(openid="wx-parent")
        other = User(openid="wx-other")
        self.db.add_all([parent, other])
        self.db.commit()

        for index in range(10):
            create_lead(appointment_payload(f"家长{index}"), parent_request("wx-parent"), self.db)

        with self.assertRaises(HTTPException) as raised:
            create_lead(appointment_payload("第十一条"), parent_request("wx-parent"), self.db)

        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.detail, "每天最多提交10条预约，请明天再试")
        created = create_lead(appointment_payload("其他微信"), parent_request("wx-other"), self.db)
        self.assertEqual(created.name, "其他微信")

    def test_appointment_history_only_returns_current_parent_records(self):
        parent = User(openid="wx-parent")
        other = User(openid="wx-other")
        self.db.add_all([parent, other])
        self.db.flush()
        self.db.add_all(
            [
                Lead(
                    user_id=parent.id,
                    campus_id="campus-1",
                    name="王女士",
                    phone="13800138000",
                    child_age=10,
                    child_name="小明",
                    child_grade="小学四年级",
                    appointment_at=datetime.now(ZoneInfo("Asia/Shanghai")) + timedelta(days=1),
                    source="trial",
                ),
                Lead(
                    user_id=other.id,
                    campus_id="campus-1",
                    name="其他家长",
                    phone="13900139000",
                    child_age=13,
                    child_name="小明",
                    child_grade="初一",
                    appointment_at=datetime.now(ZoneInfo("Asia/Shanghai")) + timedelta(days=1),
                    source="trial",
                ),
            ]
        )
        self.db.commit()

        history = get_parent_appointments(parent_request("wx-parent"), self.db)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].name, "王女士")
        self.assertEqual(history[0].phone, "13800138000")
        self.assertEqual(history[0].follow_status_label, "待联系")

    def test_parent_can_cancel_only_their_own_pending_appointment(self):
        parent = User(openid="wx-parent")
        other = User(openid="wx-other")
        self.db.add_all([parent, other])
        self.db.flush()
        appointment = Lead(
            user_id=parent.id,
            campus_id="campus-1",
            name="王女士",
            child_name="小明",
            phone="13800138000",
            child_age=10,
            child_grade="四年级",
            appointment_at=datetime.now(ZoneInfo("Asia/Shanghai")) + timedelta(days=1),
            source="trial",
        )
        self.db.add(appointment)
        self.db.commit()

        with self.assertRaises(HTTPException) as other_error:
            cancel_parent_appointment(appointment.id, parent_request("wx-other"), self.db)
        self.assertEqual(other_error.exception.status_code, 404)

        result = cancel_parent_appointment(appointment.id, parent_request("wx-parent"), self.db)
        self.assertEqual(result["message"], "预约已取消")
        self.db.refresh(appointment)
        self.assertEqual(appointment.follow_status, "cancelled")
        history = get_parent_appointments(parent_request("wx-parent"), self.db)
        self.assertEqual(history[0].follow_status_label, "已取消")

        with self.assertRaises(HTTPException) as repeated_error:
            cancel_parent_appointment(appointment.id, parent_request("wx-parent"), self.db)
        self.assertEqual(repeated_error.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
