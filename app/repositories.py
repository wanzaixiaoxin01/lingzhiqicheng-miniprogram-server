from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from math import ceil
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app import models


PUBLISHED = "published"


@dataclass(frozen=True)
class PaginatedItems:
    items: Sequence[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


PaginatedLeads = PaginatedItems


@dataclass(frozen=True)
class RollCallItem:
    student: models.Student
    enrollment: models.StudentEnrollment
    morning_present: bool
    afternoon_present: bool


@dataclass(frozen=True)
class RollCallPage:
    items: Sequence[RollCallItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    expected_count: int
    morning_count: int
    afternoon_count: int
    full_day_count: int


def paginate_query(db: Session, query, *, page: int = 1, page_size: int = 10) -> PaginatedItems:
    page_size = max(1, min(page_size, 100))
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    total_pages = max(1, ceil(total / page_size))
    page = max(1, min(page, total_pages))
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return PaginatedItems(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


ADMIN_SEARCH_COLUMNS = {
    models.Banner: (models.Banner.title,),
    models.Campus: (models.Campus.name, models.Campus.address, models.Campus.manager_name, models.Campus.phone),
    models.Course: (models.Course.title, models.Course.category, models.Course.suitable_grade),
    models.Article: (models.Article.title, models.Article.summary, models.Article.author),
    models.Material: (models.Material.title, models.Material.original_name, models.Material.summary),
    models.Setting: (models.Setting.key,),
}


def list_admin_items(
    model: type,
    db: Session,
    *,
    search: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 10,
) -> PaginatedItems:
    query = select(model)
    keyword = search.strip()
    columns = ADMIN_SEARCH_COLUMNS.get(model, ())
    if keyword and columns:
        query = query.where(or_(*(column.ilike(f"%{keyword}%") for column in columns)))
    if status.strip() and hasattr(model, "status"):
        query = query.where(model.status == status.strip())
    query = query.order_by(model.created_at.desc())
    return paginate_query(db, query, page=page, page_size=page_size)


def list_staff_page(
    db: Session,
    campus_ids: list[str] | None = None,
    *,
    search: str = "",
    status: str = "",
    roles: set[str] | None = None,
    page: int = 1,
    page_size: int = 10,
) -> PaginatedItems:
    query = select(models.AdminUser).options(
        selectinload(models.AdminUser.campus_assignments).selectinload(models.StaffCampus.campus)
    )
    if campus_ids is not None:
        query = query.where(
            models.AdminUser.id.in_(
                select(models.StaffCampus.staff_id).where(models.StaffCampus.campus_id.in_(campus_ids))
            )
        )
    if roles:
        query = query.where(models.AdminUser.role.in_(roles))
    if status.strip():
        query = query.where(models.AdminUser.status == status.strip())
    if search.strip():
        keyword = f"%{search.strip()}%"
        query = query.where(
            or_(
                models.AdminUser.display_name.ilike(keyword),
                models.AdminUser.username.ilike(keyword),
                models.AdminUser.phone.ilike(keyword),
            )
        )
    return paginate_query(db, query.order_by(models.AdminUser.created_at.desc()), page=page, page_size=page_size)


def list_scoped_students_page(
    db: Session,
    campus_ids: list[str] | None = None,
    *,
    search: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 10,
) -> PaginatedItems:
    query = select(models.Student)
    if campus_ids is not None:
        query = query.where(
            models.Student.id.in_(
                select(models.StudentEnrollment.student_id).where(models.StudentEnrollment.campus_id.in_(campus_ids))
            )
        )
    if status.strip():
        query = query.where(models.Student.status == status.strip())
    if search.strip():
        keyword = f"%{search.strip()}%"
        query = query.where(
            or_(
                models.Student.name.ilike(keyword),
                models.Student.school.ilike(keyword),
                models.Student.guardian_name.ilike(keyword),
                models.Student.guardian_phone.ilike(keyword),
            )
        )
    return paginate_query(db, query.order_by(models.Student.created_at.desc()), page=page, page_size=page_size)


def list_scoped_enrollments_page(
    db: Session,
    campus_ids: list[str] | None = None,
    *,
    search: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 10,
) -> PaginatedItems:
    query = select(models.StudentEnrollment).join(models.StudentEnrollment.student).join(models.StudentEnrollment.campus)
    if campus_ids is not None:
        query = query.where(models.StudentEnrollment.campus_id.in_(campus_ids))
    if status.strip():
        query = query.where(models.StudentEnrollment.status == status.strip())
    if search.strip():
        keyword = f"%{search.strip()}%"
        query = query.where(
            or_(
                models.Student.name.ilike(keyword),
                models.Campus.name.ilike(keyword),
                models.StudentEnrollment.service_type.ilike(keyword),
            )
        )
    return paginate_query(db, query.order_by(models.StudentEnrollment.created_at.desc()), page=page, page_size=page_size)


def list_scoped_attendance_page(
    db: Session,
    campus_ids: list[str] | None = None,
    *,
    search: str = "",
    attendance_date: date | None = None,
    page: int = 1,
    page_size: int = 10,
) -> PaginatedItems:
    query = select(models.AttendanceRecord).join(models.AttendanceRecord.student).join(models.AttendanceRecord.campus)
    if campus_ids is not None:
        query = query.where(models.AttendanceRecord.campus_id.in_(campus_ids))
    if attendance_date is not None:
        query = query.where(models.AttendanceRecord.attendance_date == attendance_date)
    if search.strip():
        keyword = f"%{search.strip()}%"
        query = query.where(
            or_(
                models.Student.name.ilike(keyword),
                models.Campus.name.ilike(keyword),
                models.AttendanceRecord.service_type.ilike(keyword),
            )
        )
    query = query.order_by(models.AttendanceRecord.attendance_date.desc(), models.AttendanceRecord.created_at.desc())
    return paginate_query(db, query, page=page, page_size=page_size)


def list_roll_call_roster(
    db: Session,
    campus_id: str,
    attendance_date: date,
    *,
    search: str = "",
    page: int = 1,
    page_size: int = 10,
) -> RollCallPage:
    query = (
        select(models.StudentEnrollment)
        .join(models.StudentEnrollment.student)
        .options(selectinload(models.StudentEnrollment.student))
        .where(
            models.StudentEnrollment.campus_id == campus_id,
            models.StudentEnrollment.status == "active",
            models.Student.status == "active",
        )
        .order_by(models.Student.created_at.desc(), models.StudentEnrollment.created_at.desc())
    )
    keyword = search.strip()
    if keyword:
        pattern = f"%{keyword}%"
        query = query.where(
            or_(
                models.Student.name.ilike(pattern),
                models.Student.school.ilike(pattern),
                models.Student.guardian_name.ilike(pattern),
                models.Student.guardian_phone.ilike(pattern),
            )
        )

    enrollments = list(db.scalars(query).all())
    unique_enrollments: list[models.StudentEnrollment] = []
    seen_students: set[str] = set()
    for enrollment in enrollments:
        if enrollment.student_id in seen_students:
            continue
        seen_students.add(enrollment.student_id)
        unique_enrollments.append(enrollment)

    records = []
    if seen_students:
        records = list(
            db.scalars(
                select(models.AttendanceRecord).where(
                    models.AttendanceRecord.campus_id == campus_id,
                    models.AttendanceRecord.attendance_date == attendance_date,
                    models.AttendanceRecord.student_id.in_(seen_students),
                )
            ).all()
        )
    record_by_key = {
        (record.student_id, record.service_type): record for record in records
    }
    all_items = []
    for enrollment in unique_enrollments:
        record = record_by_key.get((enrollment.student_id, enrollment.service_type))
        all_items.append(
            RollCallItem(
                student=enrollment.student,
                enrollment=enrollment,
                morning_present=bool(record and record.morning_present),
                afternoon_present=bool(record and record.afternoon_present),
            )
        )

    total = len(all_items)
    total_pages = max(1, ceil(total / page_size))
    current_page = min(max(page, 1), total_pages)
    start = (current_page - 1) * page_size
    return RollCallPage(
        items=all_items[start:start + page_size],
        total=total,
        page=current_page,
        page_size=page_size,
        total_pages=total_pages,
        expected_count=total,
        morning_count=sum(item.morning_present for item in all_items),
        afternoon_count=sum(item.afternoon_present for item in all_items),
        full_day_count=sum(
            item.morning_present and item.afternoon_present for item in all_items
        ),
    )


def set_roll_call_attendance(
    db: Session,
    *,
    student_id: str,
    campus_id: str,
    attendance_date: date,
    period: str,
    present: bool,
    recorded_by: str | None,
) -> models.AttendanceRecord | None:
    if period not in {"morning", "afternoon"}:
        raise ValueError("无效的点名时段")
    enrollment = db.scalar(
        select(models.StudentEnrollment)
        .join(models.StudentEnrollment.student)
        .where(
            models.StudentEnrollment.student_id == student_id,
            models.StudentEnrollment.campus_id == campus_id,
            models.StudentEnrollment.status == "active",
            models.Student.status == "active",
        )
        .order_by(models.StudentEnrollment.created_at.desc())
    )
    if enrollment is None:
        raise ValueError("学生没有该网点的有效报名")

    record = db.scalar(
        select(models.AttendanceRecord).where(
            models.AttendanceRecord.student_id == student_id,
            models.AttendanceRecord.campus_id == campus_id,
            models.AttendanceRecord.attendance_date == attendance_date,
            models.AttendanceRecord.service_type == enrollment.service_type,
        )
    )
    if record is None and not present:
        return None
    if record is None:
        record = models.AttendanceRecord(
            student_id=student_id,
            campus_id=campus_id,
            course_id=enrollment.course_id,
            attendance_date=attendance_date,
            service_type=enrollment.service_type,
            recorded_by=recorded_by,
        )
        db.add(record)

    setattr(record, f"{period}_present", present)
    record.recorded_by = recorded_by
    db.flush()
    if not record.morning_present and not record.afternoon_present:
        db.delete(record)
        db.flush()
        return None
    return record


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
        "today_leads": db.scalar(
            select(func.count(models.Lead.id)).where(func.date(models.Lead.created_at) == date.today())
        ) or 0,
        "pending_leads": db.scalar(select(func.count(models.Lead.id)).where(models.Lead.follow_status == "pending")) or 0,
        "published_campuses": db.scalar(select(func.count(models.Campus.id)).where(models.Campus.status == PUBLISHED)) or 0,
        "published_articles": db.scalar(select(func.count(models.Article.id)).where(models.Article.status == PUBLISHED)) or 0,
    }


def list_admin_leads(
    db: Session,
    *,
    follow_status: str = "",
    parent_name: str = "",
    phone: str = "",
    page: int = 1,
    page_size: int = 10,
) -> PaginatedItems:
    filters = []
    if follow_status.strip():
        filters.append(models.Lead.follow_status == follow_status.strip())
    if parent_name.strip():
        filters.append(models.Lead.name.ilike(f"%{parent_name.strip()}%"))
    phone_digits = "".join(character for character in phone if character.isdigit())
    if phone_digits:
        normalized_phone = func.replace(func.replace(models.Lead.phone, "-", ""), " ", "")
        filters.append(normalized_phone.like(f"%{phone_digits}%"))

    query = (
        select(models.Lead)
        .where(*filters)
        .order_by(models.Lead.created_at.desc())
    )
    return paginate_query(db, query, page=page, page_size=page_size)


def list_latest_pending_leads(db: Session, limit: int = 8) -> Sequence[models.Lead]:
    return db.scalars(
        select(models.Lead)
        .where(models.Lead.follow_status == "pending")
        .order_by(models.Lead.created_at.desc())
        .limit(limit)
    ).all()


def admin_list(model: type, db: Session) -> Sequence[Any]:
    return db.scalars(select(model).order_by(model.created_at.desc())).all()
