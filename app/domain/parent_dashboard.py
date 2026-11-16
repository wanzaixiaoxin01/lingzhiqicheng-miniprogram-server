from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import models
from app.domain.parent_binding import link_unbound_students_by_phone, normalize_phone


def mask_phone(value: str | None) -> str:
    phone = normalize_phone(value)
    if len(phone) >= 7:
        return f"{phone[:3]}****{phone[-4:]}"
    return phone


def attendance_period_label(morning_present: bool, afternoon_present: bool) -> str:
    if morning_present and afternoon_present:
        return "全天"
    if morning_present:
        return "上午"
    if afternoon_present:
        return "下午"
    return "未到"


def build_parent_dashboard(db: Session, parent: models.User) -> dict:
    link_unbound_students_by_phone(db, parent)
    students = list(
        db.scalars(
            select(models.Student)
            .options(
                selectinload(models.Student.enrollments).selectinload(models.StudentEnrollment.campus),
                selectinload(models.Student.enrollments).selectinload(models.StudentEnrollment.course),
                selectinload(models.Student.attendance_records).selectinload(models.AttendanceRecord.campus),
                selectinload(models.Student.attendance_records).selectinload(models.AttendanceRecord.course),
            )
            .where(models.Student.guardian_user_id == parent.id, models.Student.status == "active")
            .order_by(models.Student.created_at.desc())
        ).all()
    )

    student_payloads = []
    for student in students:
        enrollments = [
            {
                "id": item.id,
                "campus_name": item.campus.name,
                "course_title": item.course.title if item.course else None,
                "service_type": item.service_type,
                "started_on": item.started_on.isoformat() if item.started_on else None,
                "ended_on": item.ended_on.isoformat() if item.ended_on else None,
                "status": item.status,
            }
            for item in student.enrollments
            if item.status == "active"
        ]
        records = sorted(
            student.attendance_records,
            key=lambda item: (item.attendance_date, item.created_at),
            reverse=True,
        )
        attendance_records = [
            {
                "id": item.id,
                "attendance_date": item.attendance_date.isoformat(),
                "campus_name": item.campus.name,
                "course_title": item.course.title if item.course else None,
                "service_type": item.service_type,
                "note": item.note,
                "morning_present": item.morning_present,
                "afternoon_present": item.afternoon_present,
                "attendance_period_label": attendance_period_label(
                    item.morning_present, item.afternoon_present
                ),
            }
            for item in records
        ]
        student_payloads.append({
            "id": student.id,
            "name": student.name,
            "grade": student.grade,
            "school": student.school,
            "attendance_count": len(attendance_records),
            "enrollments": enrollments,
            "attendance_records": attendance_records,
        })

    return {
        "phone_masked": mask_phone(parent.phone),
        "needs_phone_authorization": not bool(normalize_phone(parent.phone)),
        "students": student_payloads,
    }
