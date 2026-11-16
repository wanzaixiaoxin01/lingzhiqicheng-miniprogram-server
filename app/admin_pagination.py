from urllib.parse import urlencode


def pagination_context(result, base_path: str, filters: dict[str, str]) -> dict:
    def page_url(page_number: int) -> str:
        query = {key: value for key, value in filters.items() if value}
        query["page"] = page_number
        return f"{base_path}?{urlencode(query)}"

    start_page = max(1, result.page - 2)
    end_page = min(result.total_pages, start_page + 4)
    start_page = max(1, end_page - 4)
    return {
        "pagination": result,
        "page_links": [
            {"number": number, "url": page_url(number)}
            for number in range(start_page, end_page + 1)
        ],
        "previous_url": page_url(result.page - 1) if result.page > 1 else "",
        "next_url": page_url(result.page + 1) if result.page < result.total_pages else "",
        "current_url": page_url(result.page),
    }
