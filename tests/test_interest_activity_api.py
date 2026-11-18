import unittest
from types import SimpleNamespace

from app.routes.public_api import course_payload


class InterestActivityApiTest(unittest.TestCase):
    def test_course_payload_exposes_absolute_cover_url(self):
        course = SimpleNamespace(
            id="interest-programming",
            title="编程与逻辑",
            category="编程与逻辑",
            cover_url="/uploads/courses/activity.jpg",
            summary="简介",
            suitable_grade="小学 / 初中",
            service_period="按主题活动安排",
            price=None,
            original_price=None,
            price_text="预约咨询",
            tags=["逻辑训练"],
            content="详情",
            sort_order=1,
            status="published",
        )

        payload = course_payload(course, "https://miniapp.example.test")

        self.assertEqual(payload["cover_url"], "https://miniapp.example.test/uploads/courses/activity.jpg")
        self.assertEqual(payload["title"], "编程与逻辑")


if __name__ == "__main__":
    unittest.main()
