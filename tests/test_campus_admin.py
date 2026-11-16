import unittest
from types import SimpleNamespace

from app.routes.admin_pages import campus_values, display_resource_status


class CampusAdminFormTest(unittest.TestCase):
    def test_published_campus_status_is_displayed_as_normal(self):
        campus = SimpleNamespace(status="published")

        self.assertEqual(display_resource_status("campuses", campus), "正常")

    def test_business_hours_defaults_to_weekend_schedule(self):
        values = campus_values(
            {
                "name": "莲花服务点",
                "address": "漯河市",
                "manager_name": "周老师",
                "phone": "13800000000",
            }
        )

        self.assertEqual(values["manager_name"], "周老师")
        self.assertEqual(values["business_hours"], "周六 09:00-18:00")


if __name__ == "__main__":
    unittest.main()
