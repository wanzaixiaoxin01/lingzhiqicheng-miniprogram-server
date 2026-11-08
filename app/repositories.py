from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models


PUBLISHED = "published"


def staff_campus_ids(db: Session, staff_id: str | None) -> list[str] | None:
    if not staff_id:
        return None
    return list(db.scalars(select(models.StaffCampus.campus_id).where(models.StaffCampus.staff_id == staff_id)))


def list_staff(db: Session, campus_ids: list[str] | None = None) -> Sequence[models.AdminUser]:
    query = select(models.AdminUser).order_by(models.AdminUser.created_at.desc())
    if campus_ids is not None:
        query = query.where(
            models.AdminUser.id.in_(
                select(models.StaffCampus.staff_id).where(models.StaffCampus.campus_id.in_(campus_ids))
            )
        )
    return db.scalars(query).all()


def list_scoped_students(db: Session, campus_ids: list[str] | None = None) -> Sequence[models.Student]:
    query = select(models.Student).order_by(models.Student.created_at.desc())
    if campus_ids is not None:
        query = query.where(
            models.Student.id.in_(
                select(models.StudentEnrollment.student_id).where(models.StudentEnrollment.campus_id.in_(campus_ids))
            )
        )
    return db.scalars(query).all()


def list_scoped_enrollments(db: Session, campus_ids: list[str] | None = None) -> Sequence[models.StudentEnrollment]:
    query = select(models.StudentEnrollment).order_by(models.StudentEnrollment.created_at.desc())
    if campus_ids is not None:
        query = query.where(models.StudentEnrollment.campus_id.in_(campus_ids))
    return db.scalars(query).all()


def list_scoped_attendance(db: Session, campus_ids: list[str] | None = None) -> Sequence[models.AttendanceRecord]:
    query = select(models.AttendanceRecord).order_by(
        models.AttendanceRecord.attendance_date.desc(), models.AttendanceRecord.created_at.desc()
    )
    if campus_ids is not None:
        query = query.where(models.AttendanceRecord.campus_id.in_(campus_ids))
    return db.scalars(query).all()


def dashboard_operations_metrics(db: Session, campus_ids: list[str] | None = None) -> dict[str, int]:
    student_query = select(func.count(models.Student.id)).where(models.Student.status == "active")
    visit_query = select(func.count(models.AttendanceRecord.id))
    if campus_ids is not None:
        student_query = student_query.where(
            models.Student.id.in_(
                select(models.StudentEnrollment.student_id).where(models.StudentEnrollment.campus_id.in_(campus_ids))
            )
        )
        visit_query = visit_query.where(models.AttendanceRecord.campus_id.in_(campus_ids))
    return {
        "active_students": db.scalar(student_query) or 0,
        "attendance_records": db.scalar(visit_query) or 0,
    }


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


def list_published_materials(db: Session) -> Sequence[models.Material]:
    return db.scalars(
        select(models.Material)
        .where(models.Material.status == PUBLISHED)
        .order_by(models.Material.created_at.desc())
    ).all()


def get_published_material(db: Session, material_id: str) -> models.Material | None:
    return db.scalar(select(models.Material).where(models.Material.id == material_id, models.Material.status == PUBLISHED))


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
        "published_campuses": db.scalar(select(func.count(models.Campus.id)).where(models.Campus.status == PUBLISHED)) or 0,
        "published_articles": db.scalar(select(func.count(models.Article.id)).where(models.Article.status == PUBLISHED)) or 0,
    }


def admin_list(model: type, db: Session) -> Sequence[Any]:
    return db.scalars(select(model).order_by(model.created_at.desc())).all()
