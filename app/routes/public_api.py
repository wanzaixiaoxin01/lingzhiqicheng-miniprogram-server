from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.domain.leads import validate_lead_input
from app.db import get_db
from app import repositories
from app.schemas import ArticleOut, BannerOut, CampusOut, CourseOut, LeadOut


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


@router.post("/leads", status_code=201)
def create_lead(payload: dict, db: Session = Depends(get_db)) -> LeadOut:
    result = validate_lead_input(payload)
    if not result.ok:
        raise HTTPException(status_code=400, detail={"error": "VALIDATION_ERROR", "fields": result.errors})

    lead = repositories.create_lead(db, result.value)
    return LeadOut.model_validate(lead)
