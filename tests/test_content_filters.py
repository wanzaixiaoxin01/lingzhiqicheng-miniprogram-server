import unittest

from app.domain.content import get_published_items, sort_by_sort_order


class ContentFiltersTest(unittest.TestCase):
    def test_get_published_items_returns_only_published_items(self):
        items = [
            {"id": "1", "title": "首页 Banner", "status": "published"},
            {"id": "2", "title": "草稿课程", "status": "draft"},
            {"id": "3", "title": "下架课程", "status": "archived"},
        ]

        self.assertEqual(
            get_published_items(items),
            [{"id": "1", "title": "首页 Banner", "status": "published"}],
        )

    def test_sort_by_sort_order_sorts_ascending(self):
        items = [
            {"id": "b", "title": "课程 B", "sort_order": 20},
            {"id": "a", "title": "课程 A", "sort_order": 10},
            {"id": "c", "title": "课程 C"},
        ]

        self.assertEqual([item["id"] for item in sort_by_sort_order(items)], ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()
