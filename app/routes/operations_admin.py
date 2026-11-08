import secrets
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, repositories
from app.auth import AdminIdentity, ROLE_ADMIN, ROLE_MANAGER, hash_password, require_admin
from app.config import settings
from app.db import get_db
from app.domain.staff_access import can_access_resource
from app.paths import TEMPLATES_DIR


router = APIRouter(dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def identity(request: Request) -> AdminIdentity:
    current = getattr(request.state, "admin_identity", None)
    if current is None:
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})
    return current


def ensure_access(request: Request, resource: str) -> AdminIdentity:
    current = identity(request)
    if not can_access_resource(current.role, resource):
        raise HTTPException(status_code=403, detail="没有权限访问该功能")
    return current


def scoped_campus_ids(db: Session, current: AdminIdentity) -> list[str] | None:
    if current.role == ROLE_ADMIN or current.id is None:
        return None
    return repositories.staff_campus_ids(db, current.id) or []


def campus_allowed(db: Session, current: AdminIdentity, campus_id: str) -> bool:
    allowed = scoped_campus_ids(db, current)
    return allowed is None or campus_id in allowed


def student_allowed(
    db: Session,
    current: AdminIdentity,
    student_id: str,
    campus_id: str,
    *,
    require_target_campus: bool = False,
) -> bool:
    if not campus_allowed(db, current, campus_id):
        return False
    student = db.get(models.Student, student_id)
    if student is None:
        return False
    allowed = scoped_campus_ids(db, current)
    if allowed is None:
        return True
    enrolled_campuses = {enrollment.campus_id for enrollment in student.enrollments}
    if require_target_campus:
        return campus_id in enrolled_campuses and campus_id in allowed
    return bool(enrolled_campuses.intersection(allowed))


def render(request: Request, template: str, context: dict):
    return templates.TemplateResponse(
        request,
        template,
        {
            **context,
            "admin_role": getattr(request.state, "admin_role", ROLE_ADMIN),
            "section": context.get("resource", ""),
        },
    )


def text(form, key: str, default: str = "") -> str:
    value = form.get(key, default)
    return value.strip() if isinstance(value, str) else default


def selected_values(form, key: str) -> list[str]:
    values = form.getlist(key) if hasattr(form, "getlist") else form.get(key, [])
    if isinstance(values, str):
        values = [values]
    return [value.strip() for value in values if isinstance(value, str) and value.strip()]


def parse_date(value: str, fallback: date | None = None) -> date | None:
    if not value:
        return fallback
    try:
        return date.fromisoformat(value)
    except ValueError:
        return fallback


def new_binding_code() -> str:
    return secrets.token_hex(4).upper()


def staff_context(db: Session, current: AdminIdentity) -> dict:
    campuses = db.scalars(select(models.Campus).order_by(models.Campus.name)).all()
    campus_ids = scoped_campus_ids(db, current)
    if campus_ids is not None:
        campuses = [campus for campus in campuses if campus.id in campus_ids]
    roles = (
        [("admin", "平台管理员"), ("manager", "网点负责人"), ("teacher", "老师")]
        if current.role == ROLE_ADMIN
        else [("teacher", "老师")]
    )
    return {"campuses": campuses, "staff_roles": roles}


def staff_allowed(db: Session, current: AdminIdentity, staff: models.AdminUser) -> bool:
    if current.role == ROLE_ADMIN:
        return True
    if current.role != ROLE_MANAGER or staff.role != "teacher":
        return False
    allowed_campuses = set(scoped_campus_ids(db, current) or [])
    assigned_campuses = {assignment.campus_id for assignment in staff.campus_assignments}
    return bool(allowed_campuses.intersection(assigned_campuses))


def validate_staff_campuses(db: Session, current: AdminIdentity, campus_ids: list[str]) -> None:
    if current.role == ROLE_ADMIN:
        return
    allowed_campuses = set(scoped_campus_ids(db, current) or [])
    if not campus_ids or not set(campus_ids).issubset(allowed_campuses):
        raise HTTPException(status_code=400, detail="只能分配到自己负责的智习室网点")


@router.get("/staff")
def list_staff(request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "staff")
    items = repositories.list_staff(db, scoped_campus_ids(db, current))
    if current.role != ROLE_ADMIN:
        items = [item for item in items if item.role == "teacher"]
    return render(
        request,
        "operations_list.html",
        {
            "resource": "staff",
            "title": "老师管理",
            "items": items,
        },
    )


@router.get("/staff/new")
def new_staff(request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "staff")
    return render(
        request,
        "operations_form.html",
        {
            "resource": "staff",
            "title": "新增老师",
            "item": None,
            "selected_campuses": [],
            **staff_context(db, current),
        },
    )


@router.post("/staff")
async def create_staff(request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "staff")
    form = await request.form()
    username = text(form, "username")
    password = text(form, "password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="账号和初始密码不能为空")
    role = text(form, "role", "teacher") if current.role == ROLE_ADMIN else "teacher"
    if role not in {"admin", "manager", "teacher"}:
        raise HTTPException(status_code=400, detail="账号角色无效")
    campus_ids = selected_values(form, "campus_ids")
    validate_staff_campuses(db, current, campus_ids)
    staff = models.AdminUser(
        username=username,
        display_name=text(form, "display_name") or username,
        phone=text(form, "phone") or None,
        password_hash=hash_password(password),
        role=role,
        status=text(form, "status", "active"),
    )
    db.add(staff)
    try:
        db.flush()
        for campus_id in campus_ids:
            if db.get(models.Campus, campus_id) is not None:
                db.add(models.StaffCampus(staff_id=staff.id, campus_id=campus_id))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="账号已存在") from exc
    return redirect("/admin/staff")


@router.get("/staff/{item_id}/edit")
def edit_staff(item_id: str, request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "staff")
    item = db.get(models.AdminUser, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not staff_allowed(db, current, item):
        raise HTTPException(status_code=403, detail="没有权限管理该账号")
    return render(
        request,
        "operations_form.html",
        {
            "resource": "staff",
            "title": "编辑老师或负责人" if current.role == ROLE_ADMIN else "编辑老师",
            "item": item,
            "selected_campuses": [assignment.campus_id for assignment in item.campus_assignments],
            **staff_context(db, current),
        },
    )


@router.post("/staff/{item_id}")
async def update_staff(item_id: str, request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "staff")
    item = db.get(models.AdminUser, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not staff_allowed(db, current, item):
        raise HTTPException(status_code=403, detail="没有权限管理该账号")
    form = await request.form()
    item.display_name = text(form, "display_name") or item.display_name
    item.phone = text(form, "phone") or None
    role = text(form, "role", item.role) if current.role == ROLE_ADMIN else "teacher"
    if role not in {"admin", "manager", "teacher"}:
        raise HTTPException(status_code=400, detail="账号角色无效")
    item.role = role
    item.status = text(form, "status", item.status)
    password = text(form, "password")
    if password:
        item.password_hash = hash_password(password)
    campus_ids = selected_values(form, "campus_ids")
    validate_staff_campuses(db, current, campus_ids)
    item.campus_assignments.clear()
    for campus_id in campus_ids:
        if db.get(models.Campus, campus_id) is not None:
            item.campus_assignments.append(models.StaffCampus(campus_id=campus_id))
    db.commit()
    return redirect("/admin/staff")


@router.post("/staff/{item_id}/delete")
def delete_staff(item_id: str, request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "staff")
    item = db.get(models.AdminUser, item_id)
    if item is not None:
        if not staff_allowed(db, current, item):
            raise HTTPException(status_code=403, detail="没有权限管理该账号")
        item.status = "disabled"
        db.commit()
    return redirect("/admin/staff")


@router.get("/students")
def list_students(request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "students")
    return render(
        request,
        "operations_list.html",
        {
            "resource": "students",
            "title": "学生管理",
            "items": repositories.list_scoped_students(db, scoped_campus_ids(db, current)),
        },
    )


@router.get("/students/new")
def new_student(request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "students")
    campus_ids = scoped_campus_ids(db, current)
    campuses = db.scalars(select(models.Campus).order_by(models.Campus.name)).all()
    if campus_ids is not None:
        campuses = [campus for campus in campuses if campus.id in campus_ids]
    return render(
        request,
        "operations_form.html",
        {
            "resource": "students",
            "title": "新增学生",
            "item": None,
            "campuses": campuses,
            "selected_campus": "",
        },
    )


@router.post("/students")
async def create_student(request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "students")
    form = await request.form()
    campus_id = text(form, "campus_id")
    if not campus_id or not campus_allowed(db, current, campus_id):
        raise HTTPException(status_code=400, detail="请选择有权限管理的智习室网点")
    student = models.Student(
        name=text(form, "name"),
        grade=text(form, "grade"),
        gender=text(form, "gender") or None,
        school=text(form, "school") or None,
        guardian_name=text(form, "guardian_name") or None,
        guardian_phone=text(form, "guardian_phone") or None,
        binding_code=new_binding_code(),
        binding_code_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=text(form, "status", "active"),
        created_by=current.id,
    )
    db.add(student)
    db.flush()
    db.add(
        models.StudentEnrollment(
            student_id=student.id,
            campus_id=campus_id,
            service_type=text(form, "service_type", "智习室学习"),
            started_on=parse_date(text(form, "started_on"), date.today()),
            status="active",
        )
    )
    db.commit()
    return redirect("/admin/students")


@router.get("/students/{item_id}/edit")
def edit_student(item_id: str, request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "students")
    item = db.get(models.Student, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="学生不存在")
    if scoped_campus_ids(db, current) is not None and not any(
        enrollment.campus_id in scoped_campus_ids(db, current) for enrollment in item.enrollments
    ):
        raise HTTPException(status_code=403, detail="没有权限管理该学生")
    campus_ids = scoped_campus_ids(db, current)
    campuses = db.scalars(select(models.Campus).order_by(models.Campus.name)).all()
    if campus_ids is not None:
        campuses = [campus for campus in campuses if campus.id in campus_ids]
    first_enrollment = item.enrollments[0] if item.enrollments else None
    return render(
        request,
        "operations_form.html",
        {
            "resource": "students",
            "title": "编辑学生",
            "item": item,
            "campuses": campuses,
            "selected_campus": first_enrollment.campus_id if first_enrollment else "",
            "selected_service_type": first_enrollment.service_type if first_enrollment else "智习室学习",
        },
    )


@router.post("/students/{item_id}")
async def update_student(item_id: str, request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "students")
    item = db.get(models.Student, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="学生不存在")
    if scoped_campus_ids(db, current) is not None and not any(
        enrollment.campus_id in scoped_campus_ids(db, current) for enrollment in item.enrollments
    ):
        raise HTTPException(status_code=403, detail="没有权限管理该学生")
    form = await request.form()
    item.name = text(form, "name")
    item.grade = text(form, "grade")
    item.gender = text(form, "gender") or None
    item.school = text(form, "school") or None
    item.guardian_name = text(form, "guardian_name") or None
    item.guardian_phone = text(form, "guardian_phone") or None
    item.status = text(form, "status", item.status)
    campus_id = text(form, "campus_id")
    if campus_id and not campus_allowed(db, current, campus_id):
        raise HTTPException(status_code=400, detail="请选择有权限管理的智习室网点")
    if campus_id:
        enrollment = item.enrollments[0] if item.enrollments else models.StudentEnrollment(student_id=item.id)
        enrollment.campus_id = campus_id
        enrollment.service_type = text(form, "service_type", enrollment.service_type or "智习室学习")
        enrollment.started_on = parse_date(text(form, "started_on"), enrollment.started_on or date.today())
        enrollment.status = "active"
        if enrollment.id is None:
            db.add(enrollment)
    db.commit()
    return redirect("/admin/students")


@router.post("/students/{item_id}/delete")
def delete_student(item_id: str, request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "students")
    item = db.get(models.Student, item_id)
    if item is not None:
        if scoped_campus_ids(db, current) is not None and not any(
            enrollment.campus_id in scoped_campus_ids(db, current) for enrollment in item.enrollments
        ):
            raise HTTPException(status_code=403, detail="没有权限管理该学生")
        db.delete(item)
        db.commit()
    return redirect("/admin/students")


@router.get("/enrollments")
def list_enrollments(request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "enrollments")
    return render(
        request,
        "operations_list.html",
        {
            "resource": "enrollments",
            "title": "学生报名",
            "items": repositories.list_scoped_enrollments(db, scoped_campus_ids(db, current)),
        },
    )


@router.get("/enrollments/new")
def new_enrollment(request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "enrollments")
    campus_ids = scoped_campus_ids(db, current)
    campuses = db.scalars(select(models.Campus).order_by(models.Campus.name)).all()
    if campus_ids is not None:
        campuses = [campus for campus in campuses if campus.id in campus_ids]
    students = repositories.list_scoped_students(db, campus_ids)
    return render(
        request,
        "operations_form.html",
        {"resource": "enrollments", "title": "新增学生报名", "item": None, "campuses": campuses, "students": students},
    )


@router.post("/enrollments")
async def create_enrollment(request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "enrollments")
    form = await request.form()
    student_id = text(form, "student_id")
    campus_id = text(form, "campus_id")
    student = db.get(models.Student, student_id)
    if student is None or not student_allowed(db, current, student_id, campus_id):
        raise HTTPException(status_code=400, detail="学生或服务点无效")
    enrollment = models.StudentEnrollment(
        student_id=student_id,
        campus_id=campus_id,
        service_type=text(form, "service_type", "智习室学习"),
        started_on=parse_date(text(form, "started_on"), date.today()),
        ended_on=parse_date(text(form, "ended_on")),
        status=text(form, "status", "active"),
    )
    db.add(enrollment)
    db.commit()
    return redirect("/admin/enrollments")


@router.get("/visits")
def list_visits(request: Request, db: Session = Depends(get_db), attendance_date: str = ""):
    current = ensure_access(request, "visits")
    items = list(repositories.list_scoped_attendance(db, scoped_campus_ids(db, current)))
    selected_date = parse_date(attendance_date)
    if selected_date:
        items = [item for item in items if item.attendance_date == selected_date]
    return render(
        request,
        "operations_list.html",
        {
            "resource": "visits",
            "title": "上课记录",
            "items": items,
            "selected_date": attendance_date,
        },
    )


@router.get("/visits/new")
def new_visit(request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "visits")
    campus_ids = scoped_campus_ids(db, current)
    campuses = db.scalars(select(models.Campus).order_by(models.Campus.name)).all()
    if campus_ids is not None:
        campuses = [campus for campus in campuses if campus.id in campus_ids]
    return render(
        request,
        "operations_form.html",
        {
            "resource": "visits",
            "title": "登记上课记录",
            "item": None,
            "campuses": campuses,
            "students": repositories.list_scoped_students(db, campus_ids),
            "today": date.today().isoformat(),
        },
    )


@router.post("/visits")
async def create_visit(request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "visits")
    form = await request.form()
    student_id = text(form, "student_id")
    campus_id = text(form, "campus_id")
    student = db.get(models.Student, student_id)
    if student is None or not student_allowed(db, current, student_id, campus_id, require_target_campus=True):
        raise HTTPException(status_code=400, detail="学生或服务点无效")
    visit = models.AttendanceRecord(
        student_id=student_id,
        campus_id=campus_id,
        attendance_date=parse_date(text(form, "attendance_date"), date.today()),
        service_type=text(form, "service_type", "智习室学习"),
        recorded_by=current.id,
        note=text(form, "note") or None,
    )
    db.add(visit)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="当天该学生的同类到访记录已存在") from exc
    return redirect("/admin/visits")


@router.post("/visits/{item_id}/delete")
def delete_visit(item_id: str, request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "visits")
    item = db.get(models.AttendanceRecord, item_id)
    if item is not None:
        if not campus_allowed(db, current, item.campus_id):
            raise HTTPException(status_code=403, detail="没有权限管理该记录")
        db.delete(item)
        db.commit()
    return redirect("/admin/visits")


@router.post("/students/{item_id}/binding-code")
def regenerate_binding_code(item_id: str, request: Request, db: Session = Depends(get_db)):
    current = ensure_access(request, "students")
    item = db.get(models.Student, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="学生不存在")
    allowed = scoped_campus_ids(db, current)
    if allowed is not None and not any(enrollment.campus_id in allowed for enrollment in item.enrollments):
        raise HTTPException(status_code=403, detail="没有权限管理该学生")
    if item.guardian_user_id:
        raise HTTPException(status_code=400, detail="该学生已绑定家长，不能重新生成绑定码")
    item.binding_code = new_binding_code()
    item.binding_code_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    db.commit()
    return redirect(f"/admin/students/{item.id}/edit")
