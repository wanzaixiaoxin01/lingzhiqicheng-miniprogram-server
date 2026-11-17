import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.auth import ROLE_ADMIN
from app.db import Base
from app.routes.admin_pages import dashboard


class AdminDashboardTest(unittest.TestCase):
    def test_dashboard_renders_html_for_platform_admin(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        request = Request({"type": "http", "method": "GET", "path": "/admin/", "headers": []})
        request.state.admin_role = ROLE_ADMIN

        with Session(engine) as db:
            response = dashboard(request, db)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 200)
        self.assertIn("运营工作台", response.body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
