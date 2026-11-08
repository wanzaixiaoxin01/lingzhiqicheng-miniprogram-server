import unittest

from app.routes.admin_pages import campus_values


class CampusAdminFormTest(unittest.TestCase):
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
