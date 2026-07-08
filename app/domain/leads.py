from dataclasses import dataclass
import re
from typing import Any


MOBILE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
SOURCE_VALUES = {"trial", "course", "campus", "material", "cooperation", "manual"}


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    value: dict[str, str]
    errors: dict[str, str]


def _clean_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def validate_lead_input(input_data: dict[str, Any] | None) -> ValidationResult:
    data = input_data or {}
    value = {
        "name": _clean_text(data.get("name")),
        "phone": _clean_text(data.get("phone")),
        "child_grade": _clean_text(data.get("child_grade")),
        "source": _clean_text(data.get("source")),
        "campus_id": _clean_text(data.get("campus_id")),
        "course_id": _clean_text(data.get("course_id")),
        "message": _clean_text(data.get("message")),
    }

    errors: dict[str, str] = {}

    if not value["name"]:
        errors["name"] = "请输入家长姓名"

    if not value["phone"] or not MOBILE_PATTERN.match(value["phone"]):
        errors["phone"] = "请输入有效的手机号"

    if not value["child_grade"]:
        errors["child_grade"] = "请选择孩子年级"

    if not value["source"]:
        errors["source"] = "请选择预约来源"
    elif value["source"] not in SOURCE_VALUES:
        errors["source"] = "预约来源不正确"

    return ValidationResult(ok=not errors, value=value if not errors else {}, errors=errors)
