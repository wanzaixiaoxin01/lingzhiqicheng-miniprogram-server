from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models


PUBLISHED = "published"


def list_published_banners(db: Session) -> Sequence[models.Banner]:
    return db.scalars(
        select(models.Banner)
        .where(models.Banner.status == PUBLISHED)
        .order_by(models.Banner.sort_order, models.Banner.created_at.desc())
    ).all()


def list_published_campuses(db: Session) -> Sequence[models.Campus]:
    return db.scalars(
        select(models.Campus)
        .where(models.Campus.status == PUBLISHED)
        .order_by(models.Campus.created_at.desc())
    ).all()


def get_published_campus(db: Session, campus_id: str) -> models.Campus | None:
    return db.scalar(select(models.Campus).where(models.Campus.id == campus_id, models.Campus.status == PUBLISHED))


def list_published_courses(db: Session, category: str | None = None) -> Sequence[models.Course]:
    query = select(models.Course).where(models.Course.status == PUBLISHED)
    if category:
        query = query.where(models.Course.category == category)
    return db.scalars(query.order_by(models.Course.sort_order, models.Course.created_at.desc())).all()


def get_published_course(db: Session, course_id: str) -> models.Course | None:
    return db.scalar(select(models.Course).where(models.Course.id == course_id, models.Course.status == PUBLISHED))


def list_published_articles(db: Session, article_type: str | None = None) -> Sequence[models.Article]:
    query = select(models.Article).where(models.Article.status == PUBLISHED)
    if article_type:
        query = query.where(models.Article.type == article_type)
    return db.scalars(query.order_by(models.Article.sort_order, models.Article.created_at.desc())).all()


def get_published_article(db: Session, article_id: str) -> models.Article | None:
    return db.scalar(select(models.Article).where(models.Article.id == article_id, models.Article.status == PUBLISHED))


def create_lead(db: Session, value: dict[str, str]) -> models.Lead:
    lead = models.Lead(
        name=value["name"],
        phone=value["phone"],
        child_grade=value["child_grade"],
        source=value["source"],
        campus_id=value.get("campus_id") or None,
        course_id=value.get("course_id") or None,
        message=value.get("message") or None,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def dashboard_metrics(db: Session) -> dict[str, int]:
    return {
        "today_leads": db.scalar(select(func.count(models.Lead.id))) or 0,
        "pending_leads": db.scalar(select(func.count(models.Lead.id)).where(models.Lead.follow_status == "pending")) or 0,
        "active_courses": db.scalar(select(func.count(models.Course.id)).where(models.Course.status == PUBLISHED)) or 0,
        "published_articles": db.scalar(select(func.count(models.Article.id)).where(models.Article.status == PUBLISHED)) or 0,
    }


def admin_list(model: type, db: Session) -> Sequence[Any]:
    return db.scalars(select(model).order_by(model.created_at.desc())).all()
