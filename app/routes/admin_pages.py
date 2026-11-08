from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app import models, repositories
from app.auth import (
    ROLE_ADMIN,
    admin_session_token,
    configured_credentials_match,
    hash_password,
    require_admin,
    staff_session_token,
    verify_password,
)
from app.config import settings
from app.db import get_db
from app.domain.campuses import DEFAULT_CAMPUS_BUSINESS_HOURS
from app.domain.staff_access import can_access_resource
from app.paths import TEMPLATES_DIR
from app.services.campus_image_storage import campus_image_storage
from app.services.material_storage import material_storage


router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals.update(
    resource_title=lambda resource: {
        "banners": "Banner 管理",
        "campuses": "智习室网点管理",
        "courses": "课程管理",
        "articles": "文章/活动管理",
        "materials": "学习资料文件",
        "leads": "预约线索",
        "settings": "系统配置",
    }.get(resource, resource),
    display_name=lambda item: getattr(item, "title", None)
    or getattr(item, "name", None)
    or getattr(item, "key", None)
    or f"{getattr(item, 'name', '')} {getattr(item, 'phone', '')}".strip(),
    display_status=lambda item: getattr(item, "status", None)
    or getattr(item, "type", None)
    or getattr(item, "follow_status", None)
    or "-",
    form_action=lambda resource, item: f"/admin/{resource}/{item.id if hasattr(item, 'id') else item.key}" if item else f"/admin/{resource}",
)
templates.env.globals["status_options"] = lambda selected: Markup(
    "".join(
        f'<option value="{value}" {"selected" if selected == value else ""}>{label}</option>'
        for value, label in [("draft", "草稿"), ("published", "发布"), ("archived", "下架")]
    )
)
templates.env.globals["article_type_options"] = lambda selected: Markup(
    "".join(
        f'<option value="{value}" {"selected" if selected == value else ""}>{label}</option>'
        for value, label in [("material", "学习资料"), ("news", "教育动态"), ("activity", "活动风采")]
    )
)
templates.env.globals["default_campus_business_hours"] = DEFAULT_CAMPUS_BUSINESS_HOURS
templates.env.globals["material_file_size"] = lambda size: (
    f"{size} B"
    if size < 1024
    else f"{size / 1024:.1f} KB"
    if size < 1024 * 1024
    else f"{size / (1024 * 1024):.1f} MB"
)


MODEL_MAP = {
    "banners": models.Banner,
    "campuses": models.Campus,
    "courses": models.Course,
    "articles": models.Article,
    "materials": models.Material,
    "leads": models.Lead,
    "settings": models.Setting,
}


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def admin_role(request: Request) -> str:
    return getattr(request.state, "admin_role", ROLE_ADMIN)


def ensure_resource_access(request: Request, resource: str) -> None:
    if not can_access_resource(admin_role(request), resource):
        raise HTTPException(status_code=403, detail="没有权限访问该功能")


@router.get("/login")
def login_page(request: Request, error: str | None = None):
    return templates.TemplateResponse(request, "admin_login.html", {"error": error or ""})


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    session_token = None
    if configured_credentials_match(username, password):
        session_token = admin_session_token(username)
    else:
        staff = db.scalar(select(models.AdminUser).where(models.AdminUser.username == username))
        if staff is not None and staff.status == "active" and verify_password(password, staff.password_hash):
            session_token = staff_session_token(staff.id, staff.role)

    if session_token is None:
        return templates.TemplateResponse(
            request,
            "admin_login.html",
            {"error": "账号或密码不正确"},
            status_code=401,
        )
    response = redirect("/admin/")
    response.set_cookie(
        "admin_session",
        session_token,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        max_age=60 * 60 * 12,
    )
    return response


@router.post("/logout")
def logout(request: Request):
    response = redirect("/admin/login")
    response.delete_cookie("admin_session")
    return response


@protected_router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    role = admin_role(request)
    is_platform_admin = role == ROLE_ADMIN
    leads = repositories.admin_list(models.Lead, db)[:8] if is_platform_admin else []
    metrics = repositories.dashboard_metrics(db) if is_platform_admin else repositories.dashboard_operations_metrics(
        db, repositories.staff_campus_ids(db, getattr(request.state.admin_identity, "id", None))
    )
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"metrics": metrics, "leads": leads, "section": "dashboard", "admin_role": role},
    )


@protected_router.get("/{resource}")
def list_resource(resource: str, request: Request, db: Session = Depends(get_db)):
    ensure_resource_access(request, resource)
    model = MODEL_MAP.get(resource)
    if model is None:
        raise HTTPException(status_code=404, detail="管理资源不存在")
    items = repositories.admin_list(model, db)
    return templates.TemplateResponse(
        request,
        "resource_list.html",
        {"resource": resource, "items": items, "section": resource, "admin_role": admin_role(request)},
    )


@protected_router.get("/{resource}/new")
def new_resource(resource: str, request: Request):
    ensure_resource_access(request, resource)
    if resource not in MODEL_MAP:
        raise HTTPException(status_code=404, detail="管理资源不存在")
    return templates.TemplateResponse(
        request,
        "resource_form.html",
        {"resource": resource, "item": None, "section": resource, "admin_role": admin_role(request)},
    )


@protected_router.post("/{resource}")
async def create_resource(resource: str, request: Request, db: Session = Depends(get_db)):
    ensure_resource_access(request, resource)
    form_data = await request.form()
    if resource == "materials":
        return await create_material(form_data, db)
    if resource == "campuses":
        return await create_campus(form_data, db)
    form = dict(form_data)
    item = build_model(resource, form)
    db.add(item)
    db.commit()
    return redirect(f"/admin/{resource}")


@protected_router.get("/{resource}/{item_id}/edit")
def edit_resource(resource: str, item_id: str, request: Request, db: Session = Depends(get_db)):
    ensure_resource_access(request, resource)
    model = MODEL_MAP.get(resource)
    if model is None:
        raise HTTPException(status_code=404, detail="管理资源不存在")
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="数据不存在")
    return templates.TemplateResponse(
        request,
        "resource_form.html",
        {"resource": resource, "item": item, "section": resource, "admin_role": admin_role(request)},
    )


@protected_router.post("/{resource}/{item_id}")
async def update_resource(resource: str, item_id: str, request: Request, db: Session = Depends(get_db)):
    ensure_resource_access(request, resource)
    model = MODEL_MAP.get(resource)
    if model is None:
        raise HTTPException(status_code=404, detail="管理资源不存在")
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="数据不存在")

    form_data = await request.form()
    if resource == "materials":
        return await update_material(item, form_data, db)
    if resource == "campuses":
        return await update_campus(item, form_data, db)
    form = dict(form_data)
    apply_model_values(item, resource, form)
    db.commit()
    return redirect(f"/admin/{resource}")


@protected_router.post("/{resource}/{item_id}/delete")
def delete_resource(resource: str, item_id: str, request: Request, db: Session = Depends(get_db)):
    ensure_resource_access(request, resource)
    model = MODEL_MAP.get(resource)
    if model is None:
        raise HTTPException(status_code=404, detail="管理资源不存在")
    item = db.get(model, item_id)
    if item is not None:
        old_cover_url = item.cover_url if resource == "campuses" else None
        db.delete(item)
        db.commit()
        if resource == "materials":
            material_storage.remove(item.storage_name)
        elif resource == "campuses":
            old_storage_name = storage_name_from_url(old_cover_url)
            if old_storage_name:
                campus_image_storage.remove(old_storage_name)
    return redirect(f"/admin/{resource}")


@protected_router.post("/leads/{item_id}/status")
def update_lead_status(
    item_id: str,
    follow_status: str = Form(...),
    follow_note: str = Form(""),
    db: Session = Depends(get_db),
):
    lead = db.get(models.Lead, item_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="线索不存在")
    lead.follow_status = follow_status
    lead.follow_note = follow_note
    db.commit()
    return redirect("/admin/leads")


async def create_material(form_data, db: Session) -> RedirectResponse:
    title = text(form_data, "title")
    if not title:
        raise HTTPException(status_code=400, detail="资料标题不能为空")
    upload = form_data.get("file")
    if not isinstance(upload, UploadFile) or not upload.filename:
        raise HTTPException(status_code=400, detail="请选择资料文件")

    material_id = models.new_id()
    try:
        info, storage_name, file_size = await material_storage.save_upload(upload, material_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    item = models.Material(
        id=material_id,
        title=title,
        summary=text(form_data, "summary") or None,
        original_name=info.original_name,
        storage_name=storage_name,
        extension=info.extension,
        content_type=info.content_type,
        file_size=file_size,
        can_preview=info.can_preview,
        status=text(form_data, "status") or "published",
    )
    try:
        db.add(item)
        db.commit()
    except Exception:
        db.rollback()
        material_storage.remove(storage_name)
        raise
    return redirect("/admin/materials")


def storage_name_from_url(url: str | None) -> str | None:
    prefix = "/uploads/campuses/"
    if not url or not url.startswith(prefix):
        return None
    return url[len(prefix):]


async def create_campus(form_data, db: Session) -> RedirectResponse:
    campus_id = models.new_id()
    values = campus_values(dict(form_data))
    if not values["manager_name"]:
        raise HTTPException(status_code=400, detail="负责人姓名不能为空")
    upload = form_data.get("cover_file")
    new_storage_name = None
    if isinstance(upload, UploadFile) and upload.filename:
        try:
            _, new_storage_name, _ = await campus_image_storage.save_upload(upload, campus_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if new_storage_name:
        values["cover_url"] = campus_image_storage.url_for(new_storage_name)
    item = models.Campus(id=campus_id, **values)
    try:
        db.add(item)
        db.commit()
    except Exception:
        db.rollback()
        if new_storage_name:
            campus_image_storage.remove(new_storage_name)
        raise
    return redirect("/admin/campuses")


async def update_campus(item: models.Campus, form_data, db: Session) -> RedirectResponse:
    old_cover_url = item.cover_url
    values = campus_values(dict(form_data))
    if not values["manager_name"]:
        raise HTTPException(status_code=400, detail="负责人姓名不能为空")
    upload = form_data.get("cover_file")
    new_storage_name = None
    if isinstance(upload, UploadFile) and upload.filename:
        try:
            _, new_storage_name, _ = await campus_image_storage.save_upload(upload, item.id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    values["cover_url"] = campus_image_storage.url_for(new_storage_name) if new_storage_name else old_cover_url
    for key, value in values.items():
        setattr(item, key, value)
    try:
        db.commit()
    except Exception:
        db.rollback()
        if new_storage_name:
            campus_image_storage.remove(new_storage_name)
        raise
    old_storage_name = storage_name_from_url(old_cover_url)
    if new_storage_name and old_storage_name:
        campus_image_storage.remove(old_storage_name)
    return redirect("/admin/campuses")


async def update_material(item: models.Material, form_data, db: Session) -> RedirectResponse:
    title = text(form_data, "title")
    if not title:
        raise HTTPException(status_code=400, detail="资料标题不能为空")
    old_storage_name = item.storage_name
    upload = form_data.get("file")
    new_storage_name = None
    if isinstance(upload, UploadFile) and upload.filename:
        try:
            info, new_storage_name, file_size = await material_storage.save_upload(upload, item.id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        item.original_name = info.original_name
        item.storage_name = new_storage_name
        item.extension = info.extension
        item.content_type = info.content_type
        item.file_size = file_size
        item.can_preview = info.can_preview

    item.title = title
    item.summary = text(form_data, "summary") or None
    item.status = text(form_data, "status") or "published"
    try:
        db.commit()
    except Exception:
        db.rollback()
        if new_storage_name:
            material_storage.remove(new_storage_name)
        raise
    if new_storage_name and old_storage_name != new_storage_name:
        material_storage.remove(old_storage_name)
    return redirect("/admin/materials")


def build_model(resource: str, form: dict[str, Any]) -> Any:
    if resource == "banners":
        return models.Banner(**banner_values(form))
    if resource == "campuses":
        return models.Campus(**campus_values(form))
    if resource == "courses":
        return models.Course(**course_values(form))
    if resource == "articles":
        return models.Article(**article_values(form))
    if resource == "settings":
        return models.Setting(key=form.get("key", "").strip(), value={"text": form.get("value", "").strip()})
    raise HTTPException(status_code=400, detail="该资源不支持新增")


def apply_model_values(item: Any, resource: str, form: dict[str, Any]) -> None:
    values: dict[str, Any]
    if resource == "banners":
        values = banner_values(form)
    elif resource == "campuses":
        values = campus_values(form)
    elif resource == "courses":
        values = course_values(form)
    elif resource == "articles":
        values = article_values(form)
    elif resource == "settings":
        values = {"value": {"text": form.get("value", "").strip()}}
    else:
        values = {}
    for key, value in values.items():
        setattr(item, key, value)


def banner_values(form: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": text(form, "title"),
        "image_url": text(form, "image_url"),
        "link_type": text(form, "link_type") or None,
        "link_value": text(form, "link_value") or None,
        "sort_order": integer(form, "sort_order", 100),
        "status": text(form, "status") or "published",
    }


def campus_values(form: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": text(form, "name"),
        "cover_url": text(form, "cover_url") or None,
        "address": text(form, "address"),
        "manager_name": text(form, "manager_name") or None,
        "phone": text(form, "phone"),
        "business_hours": text(form, "business_hours") or DEFAULT_CAMPUS_BUSINESS_HOURS,
        "intro": text(form, "intro") or None,
        "status": text(form, "status") or "published",
    }


def course_values(form: dict[str, Any]) -> dict[str, Any]:
    tags = [item.strip() for item in text(form, "tags").split(",") if item.strip()]
    return {
        "title": text(form, "title"),
        "category": text(form, "category") or "智习室",
        "cover_url": text(form, "cover_url") or None,
        "summary": text(form, "summary") or None,
        "suitable_grade": text(form, "suitable_grade") or None,
        "service_period": text(form, "service_period") or None,
        "price_text": text(form, "price_text") or None,
        "tags": tags,
        "content": text(form, "content") or None,
        "sort_order": integer(form, "sort_order", 100),
        "status": text(form, "status") or "published",
    }


def article_values(form: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": text(form, "type") or "material",
        "title": text(form, "title"),
        "cover_url": text(form, "cover_url") or None,
        "summary": text(form, "summary") or None,
        "content": text(form, "content") or "",
        "author": text(form, "author") or None,
        "sort_order": integer(form, "sort_order", 100),
        "status": text(form, "status") or "published",
    }


def text(form: dict[str, Any], key: str) -> str:
    value = form.get(key, "")
    return value.strip() if isinstance(value, str) else ""


def integer(form: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(form.get(key, default))
    except (TypeError, ValueError):
        return default
