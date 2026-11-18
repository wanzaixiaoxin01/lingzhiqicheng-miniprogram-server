from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class ServicePositioningCopyTests(unittest.TestCase):
    def test_admin_navigation_uses_visit_and_notice_positioning(self):
        navigation = read("app/templates/_nav.html")

        self.assertIn("空间公告", navigation)
        self.assertIn("到店点名", navigation)
        self.assertNotIn("学习资料", navigation)
        self.assertNotIn("上课点名", navigation)


    def test_content_forms_use_activity_and_notice_labels(self):
        form = read("app/templates/resource_form.html")
        list_page = read("app/templates/resource_list.html")
        routes = read("app/routes/admin_pages.py")

        self.assertIn("活动名称", form)
        self.assertIn("公告标题", form)
        self.assertIn("公告文件", form)
        self.assertIn("空间公告文件", routes)
        self.assertIn("兴趣活动管理", routes)
        self.assertNotIn("学习资料", form)
        self.assertNotIn("课程名称", form)
        self.assertIn("'公告' if resource == 'materials'", list_page)


    def test_attendance_pages_use_store_visit_language(self):
        dashboard = read("app/templates/dashboard.html")
        roll_call = read("app/templates/attendance_roll_call.html")
        operations_list = read("app/templates/operations_list.html")
        operations_form = read("app/templates/operations_form.html")
        routes = read("app/routes/operations_admin.py")

        combined = "\n".join((dashboard, roll_call, operations_list, operations_form, routes))
        for phrase in ("到店记录", "到店点名", "到店日期", "到店率"):
            self.assertIn(phrase, combined)
        for old_phrase in ("上课记录", "上课点名", "上课日期", "到课率"):
            self.assertNotIn(old_phrase, combined)


    def test_seed_content_matches_the_service_positioning(self):
        seed = read("app/seed.py")

        self.assertIn("编程与逻辑", seed)
        self.assertIn("音乐与乐器", seed)
        self.assertIn("空间公告", seed)
        for old_phrase in ("体验课", "课后晚托", "作业管理", "AI 督学"):
            self.assertNotIn(old_phrase, seed)
