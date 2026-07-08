from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from sqlalchemy.orm import Session

from app import models, repositories
from app.db import get_db
from app.paths import TEMPLATES_DIR


router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals.update(
    resource_title=lambda resource: {
        "banners": "Banner 管理",
        "campuses": "校区管理",
        "courses": "课程管理",
        "articles": "文章/活动管理",
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


MODEL_MAP = {
    "banners": models.Banner,
    "campuses": models.Campus,
    "courses": models.Course,
    "articles": models.Article,
    "leads": models.Lead,
    "settings": models.Setting,
}


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    leads = repositories.admin_list(models.Lead, db)[:8]
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"metrics": repositories.dashboard_metrics(db), "leads": leads, "section": "dashboard"},
    )


@router.get("/{resource}")
def list_resource(resource: str, request: Request, db: Session = Depends(get_db)):
    model = MODEL_MAP.get(resource)
    if model is None:
        raise HTTPException(status_code=404, detail="管理资源不存在")
    items = repositories.admin_list(model, db)
    return templates.TemplateResponse(
        request,
        "resource_list.html",
        {"resource": resource, "items": items, "section": resource},
    )


@router.get("/{resource}/new")
def new_resource(resource: str, request: Request):
    if resource not in MODEL_MAP:
        raise HTTPException(status_code=404, detail="管理资源不存在")
    return templates.TemplateResponse(
        request,
        "resource_form.html",
        {"resource": resource, "item": None, "section": resource},
    )


@router.post("/{resource}")
async def create_resource(resource: str, request: Request, db: Session = Depends(get_db)):
    form = dict(await request.form())
    item = build_model(resource, form)
    db.add(item)
    db.commit()
    return redirect(f"/admin/{resource}")


@router.get("/{resource}/{item_id}/edit")
def edit_resource(resource: str, item_id: str, request: Request, db: Session = Depends(get_db)):
    model = MODEL_MAP.get(resource)
    if model is None:
        raise HTTPException(status_code=404, detail="管理资源不存在")
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="数据不存在")
    return templates.TemplateResponse(
        request,
        "resource_form.html",
        {"resource": resource, "item": item, "section": resource},
    )


@router.post("/{resource}/{item_id}")
async def update_resource(resource: str, item_id: str, request: Request, db: Session = Depends(get_db)):
    model = MODEL_MAP.get(resource)
    if model is None:
        raise HTTPException(status_code=404, detail="管理资源不存在")
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="数据不存在")

    form = dict(await request.form())
    apply_model_values(item, resource, form)
    db.commit()
    return redirect(f"/admin/{resource}")


@router.post("/{resource}/{item_id}/delete")
def delete_resource(resource: str, item_id: str, db: Session = Depends(get_db)):
    model = MODEL_MAP.get(resource)
    if model is None:
        raise HTTPException(status_code=404, detail="管理资源不存在")
    item = db.get(model, item_id)
    if item is not None:
        db.delete(item)
        db.commit()
    return redirect(f"/admin/{resource}")


@router.post("/leads/{item_id}/status")
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
        "phone": text(form, "phone"),
        "business_hours": text(form, "business_hours") or None,
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
