from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any
from zoneinfo import ZoneInfo


MOBILE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
SOURCE_VALUES = {"trial", "course", "campus", "material", "cooperation", "manual"}
BEIJING = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    value: dict[str, Any]
    errors: dict[str, str]


def _clean_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def validate_lead_input(
    input_data: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> ValidationResult:
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

    child_school = _clean_text(data.get("child_school"))
    if data.get("child_school") is not None and not isinstance(data["child_school"], str):
        errors["child_school"] = "请输入有效的学校名称"
    elif len(child_school) > 120:
        errors["child_school"] = "学校名称不能超过120个字"
    else:
        value["child_school"] = child_school or None

    child_name = _clean_text(data.get("child_name"))
    if data.get("child_name") is not None and not isinstance(data["child_name"], str):
        errors["child_name"] = "请输入有效的孩子姓名"
    elif len(child_name) > 80:
        errors["child_name"] = "孩子姓名不能超过80个字"
    else:
        value["child_name"] = child_name or None

    age = data.get("child_age")
    if age is None or age == "":
        value["child_age"] = None
    elif type(age) is not int or not 1 <= age <= 30:
        errors["child_age"] = "请选择1至30岁的孩子年龄"
    else:
        value["child_age"] = age

    appointment_text = _clean_text(data.get("appointment_at"))
    if not value["campus_id"]:
        errors["campus_id"] = "请选择预约网点"
    if not appointment_text:
        errors["appointment_at"] = "请选择预约日期"
    else:
        try:
            appointment_at = datetime.fromisoformat(appointment_text)
            if appointment_at.tzinfo is None:
                appointment_at = appointment_at.replace(tzinfo=BEIJING)
        except ValueError:
            errors["appointment_at"] = "预约日期格式不正确"
        else:
            current_time = now or datetime.now(BEIJING)
            if appointment_at.astimezone(BEIJING).date() < current_time.astimezone(BEIJING).date():
                errors["appointment_at"] = "请选择今天或之后的日期"
            else:
                value["appointment_at"] = appointment_at

    if not value["name"]:
        errors["name"] = "请输入家长姓名"

    if not value["phone"] or not MOBILE_PATTERN.match(value["phone"]):
        errors["phone"] = "请输入有效的手机号"

    if not value["child_grade"]:
        value["child_grade"] = None

    if not value["source"]:
        errors["source"] = "请选择预约来源"
    elif value["source"] not in SOURCE_VALUES:
        errors["source"] = "预约来源不正确"

    return ValidationResult(ok=not errors, value=value if not errors else {}, errors=errors)
