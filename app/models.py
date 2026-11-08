from datetime import date, datetime
from decimal import Decimal
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base


def new_id() -> str:
    return uuid.uuid4().hex


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Banner(Base, TimestampMixin):
    __tablename__ = "banners"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(120))
    image_url: Mapped[str] = mapped_column(String(500))
    link_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    link_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(default=100)
    status: Mapped[str] = mapped_column(String(20), default="published")


class Campus(Base, TimestampMixin):
    __tablename__ = "campuses"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120))
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address: Mapped[str] = mapped_column(String(300))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    manager_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    phone: Mapped[str] = mapped_column(String(40))
    business_hours: Mapped[str | None] = mapped_column(String(120), nullable=True)
    images: Mapped[list | None] = mapped_column(JSON, nullable=True)
    intro: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="published")

    leads: Mapped[list["Lead"]] = relationship(back_populates="campus")


class AdminUser(Base, TimestampMixin):
    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="teacher", index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    campus_assignments: Mapped[list["StaffCampus"]] = relationship(
        back_populates="staff", cascade="all, delete-orphan"
    )
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        back_populates="recorder", foreign_keys="AttendanceRecord.recorded_by"
    )


class StaffCampus(Base):
    __tablename__ = "staff_campuses"

    staff_id: Mapped[str] = mapped_column(ForeignKey("admin_users.id", ondelete="CASCADE"), primary_key=True)
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id", ondelete="CASCADE"), primary_key=True)

    staff: Mapped[AdminUser] = relationship(back_populates="campus_assignments")
    campus: Mapped[Campus] = relationship()


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(60))
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    suitable_grade: Mapped[str | None] = mapped_column(String(120), nullable=True)
    service_period: Mapped[str | None] = mapped_column(String(120), nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    original_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_text: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(default=100)
    status: Mapped[str] = mapped_column(String(20), default="published")

    leads: Mapped[list["Lead"]] = relationship(back_populates="course")


class Article(Base, TimestampMixin):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(160))
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sort_order: Mapped[int] = mapped_column(default=100)
    status: Mapped[str] = mapped_column(String(20), default="published")


class Material(Base, TimestampMixin):
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    original_name: Mapped[str] = mapped_column(String(255))
    storage_name: Mapped[str] = mapped_column(String(120), unique=True)
    extension: Mapped[str] = mapped_column(String(20))
    content_type: Mapped[str] = mapped_column(String(160))
    file_size: Mapped[int] = mapped_column(default=0)
    can_preview: Mapped[bool] = mapped_column(default=False)
    download_count: Mapped[int] = mapped_column(default=0)
    sort_order: Mapped[int] = mapped_column(default=100)
    status: Mapped[str] = mapped_column(String(20), default="published")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    openid: Mapped[str] = mapped_column(String(120), unique=True)
    unionid: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(120), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)

    children: Mapped[list["Child"]] = relationship(back_populates="user")
    students: Mapped[list["Student"]] = relationship(back_populates="guardian")
    leads: Mapped[list["Lead"]] = relationship(back_populates="user")


class Child(Base, TimestampMixin):
    __tablename__ = "children"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(80))
    grade: Mapped[str] = mapped_column(String(80))
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    school: Mapped[str | None] = mapped_column(String(120), nullable=True)

    user: Mapped[User] = relationship(back_populates="children")


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(80))
    grade: Mapped[str] = mapped_column(String(80))
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    school: Mapped[str | None] = mapped_column(String(120), nullable=True)
    guardian_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    guardian_phone: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    guardian_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    binding_code: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True)
    binding_code_expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)

    guardian: Mapped[User | None] = relationship(back_populates="students", foreign_keys=[guardian_user_id])
    enrollments: Mapped[list["StudentEnrollment"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )


class StudentEnrollment(Base, TimestampMixin):
    __tablename__ = "student_enrollments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id"), index=True)
    course_id: Mapped[str | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    service_type: Mapped[str] = mapped_column(String(80))
    started_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ended_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    student: Mapped[Student] = relationship(back_populates="enrollments")
    campus: Mapped[Campus] = relationship()
    course: Mapped["Course | None"] = relationship()


class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "campus_id",
            "attendance_date",
            "service_type",
            name="uq_attendance_student_campus_date_service",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id"), index=True)
    course_id: Mapped[str | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    attendance_date: Mapped[date] = mapped_column(Date, index=True)
    service_type: Mapped[str] = mapped_column(String(80))
    recorded_by: Mapped[str | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    student: Mapped[Student] = relationship(back_populates="attendance_records")
    campus: Mapped[Campus] = relationship()
    course: Mapped["Course | None"] = relationship()
    recorder: Mapped[AdminUser | None] = relationship(
        back_populates="attendance_records", foreign_keys=[recorded_by]
    )


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    campus_id: Mapped[str | None] = mapped_column(ForeignKey("campuses.id"), nullable=True)
    course_id: Mapped[str | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(40))
    child_grade: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(40))
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_status: Mapped[str] = mapped_column(String(30), default="pending")
    follow_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User | None] = relationship(back_populates="leads")
    campus: Mapped[Campus | None] = relationship(back_populates="leads")
    course: Mapped[Course | None] = relationship(back_populates="leads")


class Setting(Base, TimestampMixin):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
