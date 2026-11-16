import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models


@dataclass
class VerifiedPhoneBinding:
    parent: models.User
    students: list[models.Student]


def normalize_phone(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def bind_student_to_parent(
    db: Session,
    binding_code: str,
    openid: str,
    phone: str,
    *,
    nickname: str | None = None,
    avatar_url: str | None = None,
    unionid: str | None = None,
    now: datetime | None = None,
) -> models.User:
    code = (binding_code or "").strip().upper()
    wx_openid = (openid or "").strip()
    normalized_phone = normalize_phone(phone)
    if not code or not wx_openid or not normalized_phone:
        raise ValueError("绑定码、微信标识和手机号不能为空")

    student = db.scalar(select(models.Student).where(models.Student.binding_code == code))
    if student is None:
        raise ValueError("绑定码无效或已使用")

    current_time = _utc(now or datetime.now(timezone.utc))
    if student.binding_code_expires_at is not None and _utc(student.binding_code_expires_at) < current_time:
        raise ValueError("绑定码已过期，请联系服务点重新生成")

    expected_phone = normalize_phone(student.guardian_phone)
    if expected_phone and expected_phone != normalized_phone:
        raise ValueError("手机号与学生登记信息不一致")

    parent = db.scalar(select(models.User).where(models.User.openid == wx_openid))
    if student.guardian_user_id and (parent is None or student.guardian_user_id != parent.id):
        raise ValueError("该学生已绑定其他家长")
    if not expected_phone:
        student.guardian_phone = normalized_phone
    if parent is None:
        parent = models.User(
            openid=wx_openid,
            unionid=unionid,
            nickname=nickname,
            avatar_url=avatar_url,
            phone=normalized_phone,
        )
        db.add(parent)
        db.flush()
    else:
        if unionid:
            parent.unionid = unionid
        if nickname:
            parent.nickname = nickname
        if avatar_url:
            parent.avatar_url = avatar_url
        parent.phone = normalized_phone

    student.guardian_user_id = parent.id
    student.binding_code = None
    student.binding_code_expires_at = None
    db.commit()
    db.refresh(parent)
    return parent


def list_parent_students(db: Session, user_id: str) -> list[models.Student]:
    if not user_id:
        return []
    return list(
        db.scalars(
            select(models.Student)
            .where(models.Student.guardian_user_id == user_id)
            .order_by(models.Student.created_at.desc())
        ).all()
    )


def bind_students_by_verified_phone(db: Session, openid: str, phone: str) -> VerifiedPhoneBinding:
    wx_openid = (openid or "").strip()
    normalized_phone = normalize_phone(phone)
    if not wx_openid or not normalized_phone:
        raise ValueError("微信标识和授权手机号不能为空")

    parent = db.scalar(select(models.User).where(models.User.openid == wx_openid))
    candidates = list(db.scalars(select(models.Student).where(models.Student.status == "active")).all())
    students = [item for item in candidates if normalize_phone(item.guardian_phone) == normalized_phone]

    conflicting = [
        item
        for item in students
        if item.guardian_user_id and (parent is None or item.guardian_user_id != parent.id)
    ]
    if conflicting:
        raise ValueError("该学生已绑定其他微信，请联系服务点处理")

    if parent is None:
        parent = models.User(openid=wx_openid, phone=normalized_phone)
        db.add(parent)
        db.flush()
    else:
        parent.phone = normalized_phone

    for student in students:
        student.guardian_user_id = parent.id
        student.binding_code = None
        student.binding_code_expires_at = None

    db.commit()
    db.refresh(parent)
    return VerifiedPhoneBinding(parent=parent, students=students)


def link_unbound_students_by_phone(db: Session, parent: models.User) -> list[models.Student]:
    normalized_phone = normalize_phone(parent.phone)
    if not normalized_phone:
        return []
    candidates = list(
        db.scalars(
            select(models.Student).where(
                models.Student.status == "active",
                models.Student.guardian_user_id.is_(None),
            )
        ).all()
    )
    students = [item for item in candidates if normalize_phone(item.guardian_phone) == normalized_phone]
    for student in students:
        student.guardian_user_id = parent.id
        student.binding_code = None
        student.binding_code_expires_at = None
    if students:
        db.commit()
    return students
