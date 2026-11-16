import unittest
from unittest.mock import patch

from fastapi import HTTPException, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth import parent_session_token
from app.db import Base
from app.models import Student, User
from app.routes.public_api import authorize_parent_phone, get_parent_dashboard


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
        self.db.query(User).delete()
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_phone_endpoint_uses_wechat_verified_number_and_links_students(self):
        self.db.add_all([
            User(openid="wx-parent"),
            Student(name="张小明", grade="七年级", guardian_phone="13811112222"),
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

    def test_dashboard_rejects_missing_parent_session(self):
        with self.assertRaises(HTTPException) as raised:
            get_parent_dashboard(parent_request(), self.db)

        self.assertEqual(raised.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
