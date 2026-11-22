import unittest
from types import SimpleNamespace

from app.routes.admin_pages import display_resource_status


class AdminStatusDisplayTest(unittest.TestCase):
    def test_material_statuses_use_chinese_labels(self):
        self.assertEqual(display_resource_status("materials", SimpleNamespace(status="published")), "已发布")
        self.assertEqual(display_resource_status("materials", SimpleNamespace(status="draft")), "草稿")
        self.assertEqual(display_resource_status("materials", SimpleNamespace(status="archived")), "下架")

    def test_lead_statuses_use_chinese_labels(self):
        labels = {
            "pending": "待跟进",
            "contacted": "已联系",
            "visited": "已到店",
            "converted": "已成交",
            "not_considering": "暂不考虑",
            "invalid": "无效",
            "cancelled": "已取消",
        }
        for status, label in labels.items():
            with self.subTest(status=status):
                self.assertEqual(
                    display_resource_status("leads", SimpleNamespace(follow_status=status)),
                    label,
                )


if __name__ == "__main__":
    unittest.main()
