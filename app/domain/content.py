from typing import Any


def get_published_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if item.get("status") == "published"]


def sort_by_sort_order(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: (item.get("sort_order", 9_999_999), item.get("title", "")))
