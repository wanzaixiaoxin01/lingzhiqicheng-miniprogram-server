import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class AdminComponentStylesTest(unittest.TestCase):
    def test_shared_admin_tokens_and_components_exist(self):
        css = (ROOT / "app/static/admin.css").read_text()
        for token in ("--admin-primary", "--admin-control-height", ".admin-filter-bar", ".admin-table", ".admin-form", ".admin-select-trigger"):
            with self.subTest(token=token):
                self.assertIn(token, css)

    def test_high_traffic_pages_use_shared_component_classes(self):
        for template in ("resource_list.html", "operations_list.html", "resource_form.html", "operations_form.html"):
            html = (ROOT / "app/templates" / template).read_text()
            with self.subTest(template=template):
                self.assertTrue("admin-filter-bar" in html or "admin-form" in html)


if __name__ == "__main__":
    unittest.main()
