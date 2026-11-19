import unittest
from unittest.mock import patch

from fastapi import HTTPException, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth import parent_session_token
from app.db import Base
from app.models import Lead, Student, User
from app.routes.public_api import (
    authorize_parent_phone,
    create_lead,
    get_parent_appointments,
    get_parent_dashboard,
)


def parent_request(openid: str | None = None) -> Request:
    headers = []
    if openid:
        headers.append((b"authorization", f"Bearer {parent_session_token(openid)}".encode()))
    return Request({"type": "http", "headers": headers, "method": "GET", "path": "/"})


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
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_phone_endpoint_uses_wechat_verified_number_and_links_students(self):
        parent = User(openid="wx-parent")
        lead = Lead(
            name="历史预约家长",
            phone="13811112222",
            child_grade="七年级",
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
            {
                "name": "王女士",
                "phone": "13800138000",
                "child_grade": "小学四年级",
                "source": "trial",
            },
            parent_request("wx-parent"),
            self.db,
        )

        lead = self.db.get(Lead, created.id)
        self.assertEqual(lead.user_id, parent.id)

    def test_legacy_appointment_submission_without_session_remains_compatible(self):
        created = create_lead(
            {
                "name": "旧版用户",
                "phone": "13800138000",
                "child_grade": "小学四年级",
                "source": "trial",
            },
            parent_request(),
            self.db,
        )

        self.assertIsNone(self.db.get(Lead, created.id).user_id)

    def test_appointment_history_only_returns_current_parent_records(self):
        parent = User(openid="wx-parent")
        other = User(openid="wx-other")
        self.db.add_all([parent, other])
        self.db.flush()
        self.db.add_all(
            [
                Lead(
                    user_id=parent.id,
                    name="王女士",
                    phone="13800138000",
                    child_grade="小学四年级",
                    source="trial",
                ),
                Lead(
                    user_id=other.id,
                    name="其他家长",
                    phone="13900139000",
                    child_grade="初一",
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


if __name__ == "__main__":
    unittest.main()
