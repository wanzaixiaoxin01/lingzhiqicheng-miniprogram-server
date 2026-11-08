import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.domain.leads import validate_lead_input
from app.auth import parent_session_token, parse_parent_session
from app.domain.parent_binding import bind_student_to_parent, list_parent_students
from app.db import get_db
from app import repositories
from app.schemas import (
    ArticleOut,
    BannerOut,
    CampusOut,
    CourseOut,
    LeadOut,
    MaterialOut,
    ParentBindOut,
    ParentSessionOut,
    ParentStudentOut,
)
from app.services.material_storage import material_storage


router = APIRouter()


@router.get("/home")
def get_home(db: Session = Depends(get_db)) -> dict[str, list]:
    return {
        "banners": [BannerOut.model_validate(item).model_dump(mode="json") for item in repositories.list_published_banners(db)[:5]],
        "campuses": [CampusOut.model_validate(item).model_dump(mode="json") for item in repositories.list_published_campuses(db)[:3]],
        "courses": [CourseOut.model_validate(item).model_dump(mode="json") for item in repositories.list_published_courses(db)[:6]],
        "articles": [ArticleOut.model_validate(item).model_dump(mode="json") for item in repositories.list_published_articles(db)[:6]],
    }


@router.get("/campuses")
def get_campuses(db: Session = Depends(get_db)) -> list[CampusOut]:
    return [CampusOut.model_validate(item) for item in repositories.list_published_campuses(db)]


@router.get("/campuses/{campus_id}")
def get_campus(campus_id: str, db: Session = Depends(get_db)) -> CampusOut:
    campus = repositories.get_published_campus(db, campus_id)
    if campus is None:
        raise HTTPException(status_code=404, detail="校区不存在")
    return CampusOut.model_validate(campus)


@router.get("/courses")
def get_courses(category: str | None = None, db: Session = Depends(get_db)) -> list[CourseOut]:
    return [CourseOut.model_validate(item) for item in repositories.list_published_courses(db, category)]


@router.get("/courses/{course_id}")
def get_course(course_id: str, db: Session = Depends(get_db)) -> CourseOut:
    course = repositories.get_published_course(db, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="课程不存在")
    return CourseOut.model_validate(course)


@router.get("/articles")
def get_articles(type: str | None = None, db: Session = Depends(get_db)) -> list[ArticleOut]:
    return [ArticleOut.model_validate(item) for item in repositories.list_published_articles(db, type)]


@router.get("/articles/{article_id}")
def get_article(article_id: str, db: Session = Depends(get_db)) -> ArticleOut:
    article = repositories.get_published_article(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="内容不存在")
    return ArticleOut.model_validate(article)


def material_payload(material) -> dict:
    payload = MaterialOut.model_validate(material).model_dump(mode="json")
    payload["file_name"] = payload.pop("original_name")
    payload["file_size_label"] = format_file_size(material.file_size)
    base_url = settings.public_base_url.rstrip("/")
    payload["download_url"] = f"{base_url}/api/public/materials/{material.id}/download" if base_url else f"/api/public/materials/{material.id}/download"
    return payload


def format_file_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


@router.get("/materials")
def get_materials(db: Session = Depends(get_db)) -> list[dict]:
    return [material_payload(item) for item in repositories.list_published_materials(db)]


@router.get("/materials/{material_id}")
def get_material(material_id: str, db: Session = Depends(get_db)) -> dict:
    material = repositories.get_published_material(db, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="学习资料不存在")
    return material_payload(material)


@router.get("/materials/{material_id}/download")
def download_material(material_id: str, db: Session = Depends(get_db)) -> FileResponse:
    material = repositories.get_published_material(db, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="学习资料不存在")
    if not material_storage.exists(material.storage_name):
        raise HTTPException(status_code=404, detail="资料文件不存在")

    material.download_count += 1
    db.commit()
    return FileResponse(
        material_storage.path_for(material.storage_name),
        media_type=material.content_type,
        filename=material.original_name,
    )


@router.post("/leads", status_code=201)
def create_lead(payload: dict, db: Session = Depends(get_db)) -> LeadOut:
    result = validate_lead_input(payload)
    if not result.ok:
        raise HTTPException(status_code=400, detail={"error": "VALIDATION_ERROR", "fields": result.errors})

    lead = repositories.create_lead(db, result.value)
    return LeadOut.model_validate(lead)


def exchange_wechat_code(code: str) -> tuple[str, str | None]:
    if not settings.miniprogram_app_id or not settings.miniprogram_app_secret:
        raise HTTPException(status_code=503, detail="服务端尚未配置微信小程序凭据")
    query = urlencode(
        {
            "appid": settings.miniprogram_app_id,
            "secret": settings.miniprogram_app_secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    try:
        with urlopen(f"https://api.weixin.qq.com/sns/jscode2session?{query}", timeout=8) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="微信登录服务暂时不可用") from exc
    if result.get("errcode") or not result.get("openid"):
        raise HTTPException(status_code=400, detail=result.get("errmsg") or "微信登录凭据无效")
    return result["openid"], result.get("unionid")


def parent_openid(request: Request, payload_openid: str | None = None) -> str:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        session_openid = parse_parent_session(authorization[7:].strip())
        if session_openid:
            return session_openid
    if settings.app_env == "production":
        return ""
    return (request.headers.get("x-wechat-openid") or payload_openid or "").strip()


@router.post("/parent/session")
def create_parent_session(payload: dict, db: Session = Depends(get_db)) -> ParentSessionOut:
    openid = ""
    unionid = str(payload.get("unionid") or "") or None
    if settings.app_env != "production":
        openid = str(payload.get("openid") or "").strip()
    if not openid:
        code = str(payload.get("code") or "").strip()
        if not code:
            raise HTTPException(status_code=400, detail="缺少微信登录凭据")
        openid, unionid = exchange_wechat_code(code)

    parent = db.scalar(select(models.User).where(models.User.openid == openid))
    if parent is None:
        parent = models.User(openid=openid, unionid=unionid)
        db.add(parent)
    elif unionid:
        parent.unionid = unionid
    db.commit()
    return ParentSessionOut(session_token=parent_session_token(openid))


@router.post("/parent/bind", status_code=200)
def bind_parent(payload: dict, request: Request, db: Session = Depends(get_db)) -> ParentBindOut:
    openid = parent_openid(request, str(payload.get("openid") or ""))
    binding_code = str(payload.get("binding_code") or payload.get("code") or "")
    phone = str(payload.get("phone") or "")
    student = db.scalar(select(models.Student).where(models.Student.binding_code == binding_code.strip().upper()))
    try:
        bind_student_to_parent(
            db,
            binding_code,
            openid,
            phone,
            nickname=str(payload.get("nickname") or "") or None,
            avatar_url=str(payload.get("avatar_url") or "") or None,
            unionid=str(payload.get("unionid") or "") or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if student is None:
        raise HTTPException(status_code=400, detail="绑定码无效或已使用")
    return ParentBindOut(message="绑定成功", student=ParentStudentOut.model_validate(student))


@router.get("/parent/students")
def get_parent_students(
    request: Request,
    openid: str | None = None,
    db: Session = Depends(get_db),
) -> list[ParentStudentOut]:
    current_openid = parent_openid(request, openid)
    if not current_openid:
        raise HTTPException(status_code=400, detail="缺少微信用户标识")
    parent = db.scalar(select(models.User).where(models.User.openid == current_openid))
    if parent is None:
        return []
    return [ParentStudentOut.model_validate(item) for item in list_parent_students(db, parent.id)]
