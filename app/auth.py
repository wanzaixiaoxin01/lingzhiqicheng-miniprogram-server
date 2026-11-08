import hashlib
import hmac
import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.db import get_db


ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_TEACHER = "teacher"

# Use a passlib-native scheme so the admin login is not tied to a specific
# bcrypt package version on the deployment image.
password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_credentials(username: str, password: str, expected_username: str, expected_password: str) -> bool:
    return secrets.compare_digest(username, expected_username) and secrets.compare_digest(password, expected_password)


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_context.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


@dataclass(frozen=True)
class AdminIdentity:
    id: str | None
    username: str
    display_name: str
    role: str


def staff_session_token(staff_id: str, role: str) -> str:
    payload = f"staff:{staff_id}:{role}"
    signature = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def parse_staff_session(token: str | None) -> tuple[str, str] | None:
    if not token or "." not in token:
        return None
    payload, signature = token.rsplit(".", 1)
    expected = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(signature, expected):
        return None
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != "staff" or not parts[1] or not parts[2]:
        return None
    return parts[1], parts[2]


def resolve_admin_identity(request: Request, db: Session) -> AdminIdentity | None:
    token = request.cookies.get("admin_session")
    if is_admin_session(token):
        return AdminIdentity(
            id=None,
            username=settings.admin_username,
            display_name="平台管理员",
            role=ROLE_ADMIN,
        )

    parsed = parse_staff_session(token)
    if not parsed:
        return None
    staff_id, role = parsed
    staff = db.get(models.AdminUser, staff_id)
    if staff is None or staff.status != "active" or staff.role != role:
        return None
    return AdminIdentity(id=staff.id, username=staff.username, display_name=staff.display_name, role=staff.role)


def require_admin(request: Request, db: Session = Depends(get_db)) -> AdminIdentity:
    identity = resolve_admin_identity(request, db)
    if identity is not None:
        request.state.admin_identity = identity
        request.state.admin_role = identity.role
        return identity
    raise HTTPException(status_code=303, headers={"Location": "/admin/login"})


def configured_credentials_match(username: str, password: str) -> bool:
    return verify_credentials(username, password, settings.admin_username, settings.admin_password)


def admin_session_token(username: str | None = None) -> str:
    value = username or settings.admin_username
    return hmac.new(settings.secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def is_admin_session(token: str | None) -> bool:
    return bool(token) and secrets.compare_digest(token, admin_session_token())


def parent_session_token(openid: str) -> str:
    payload = f"parent:{openid.strip()}"
    signature = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def parse_parent_session(token: str | None) -> str | None:
    if not token or "." not in token:
        return None
    payload, signature = token.rsplit(".", 1)
    expected = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(signature, expected):
        return None
    parts = payload.split(":", 1)
    if len(parts) != 2 or parts[0] != "parent" or not parts[1]:
        return None
    return parts[1]
