import asyncio
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app import models
from app.auth import AdminIdentity, ROLE_ADMIN
from app.db import Base, _ensure_schema_compatibility
from app.domain.parent_dashboard import validity_label
from app.routes.operations_admin import (
    create_student,
    student_service_type,
    student_validity_dates,
    validate_enrollment_date_overlap,
)
from app.repositories import select_parent_enrollment


class StudentValidityTest(unittest.TestCase):
    def test_duration_labels(self):
        start = date(2026, 11, 24)
        for end, label in [(date(2026, 11, 30), "7天"), (date(2026, 12, 23), "1个月"), (date(2027, 2, 23), "3个月"), (date(2027, 5, 23), "半年"), (date(2027, 11, 23), "1年"), (start, "1天")]:
            self.assertEqual(validity_label(start, end), label)
        self.assertEqual(validity_label(None, None), "待完善")
        self.assertEqual(validity_label(date(2028, 2, 29), date(2029, 2, 27)), "1年")

    def test_date_validation(self):
        for form in [{}, {"started_on": "2026-11-24", "ended_on": "bad"}, {"started_on": "2026-11-24", "ended_on": "2026-11-23"}]:
            with self.assertRaises(HTTPException):
                student_validity_dates(form)
        self.assertEqual(student_validity_dates({"started_on": "2026-11-24", "ended_on": "2026-11-30"}), (date(2026, 11, 24), date(2026, 11, 30)))

    def test_enrollment_date_overlap_uses_closed_intervals_and_allows_adjacent_days(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)
        campus = models.Campus(name="中心店", address="测试地址", phone="13800138000")
        student = models.Student(name="学生", grade="四年级")
        db.add_all([campus, student])
        db.flush()
        existing = models.StudentEnrollment(
            student_id=student.id,
            campus_id=campus.id,
            service_type="自习室场地服务",
            started_on=date(2026, 1, 1),
            ended_on=date(2026, 1, 31),
        )
        db.add(existing)
        db.commit()

        validate_enrollment_date_overlap(db, student.id, date(2026, 2, 1), date(2026, 2, 28))
        with self.assertRaisesRegex(HTTPException, "报名日期不能与已有记录重叠"):
            validate_enrollment_date_overlap(db, student.id, date(2026, 1, 31), date(2026, 2, 10))
        validate_enrollment_date_overlap(
            db, student.id, date(2026, 1, 1), date(2026, 1, 31), exclude_id=existing.id
        )
        db.close()
        engine.dispose()

    def test_parent_enrollment_selection_prefers_current_then_future_then_expired(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)
        campus = models.Campus(name="中心店", address="测试地址", phone="13800138000")
        student = models.Student(name="学生", grade="四年级")
        db.add_all([campus, student])
        db.flush()
        records = [
            models.StudentEnrollment(student_id=student.id, campus_id=campus.id, service_type="旧", status="active", started_on=date(2025, 1, 1), ended_on=date(2025, 12, 31)),
            models.StudentEnrollment(student_id=student.id, campus_id=campus.id, service_type="当前", status="active", started_on=date(2026, 1, 1), ended_on=date(2026, 12, 31)),
            models.StudentEnrollment(student_id=student.id, campus_id=campus.id, service_type="未来", status="active", started_on=date(2027, 1, 1), ended_on=date(2027, 12, 31)),
        ]
        db.add_all(records)
        db.commit()
        assert select_parent_enrollment(records, date(2026, 6, 1)).service_type == "当前"
        assert select_parent_enrollment(records, date(2026, 12, 31) + __import__("datetime").timedelta(days=1)).service_type == "未来"
        assert select_parent_enrollment(records, date(2028, 1, 1)).service_type == "未来"
        db.close()
        engine.dispose()

    def test_student_service_is_a_controlled_option(self):
        self.assertEqual(student_service_type({"service_type": "自习室场地服务"}), "自习室场地服务")
        for form in ({}, {"service_type": "任意服务"}):
            with self.assertRaises(HTTPException):
                student_service_type(form)

    def test_student_form_uses_select_dates_and_note(self):
        template = (Path(__file__).parents[1] / "app/templates/operations_form.html").read_text(encoding="utf-8")
        self.assertIn('<select name="service_type" required>', template)
        self.assertIn('data-validity-range', template)
        self.assertIn('name="started_on" type="text"', template)
        self.assertIn('name="ended_on" type="text"', template)
        self.assertIn('student-validity-range.css?v=20261124-2', template)
        self.assertIn('student-validity-range.js', template)
        self.assertIn('admin-form.js?v=20261125-1', template)
        self.assertNotIn('class="validity-presets"', template)
        self.assertIn('<textarea name="note"', template)

    def test_student_detail_contains_inline_enrollment_form(self):
        template = (Path(__file__).parents[1] / "app/templates/student_detail.html").read_text(encoding="utf-8")
        self.assertIn('action="/admin/students/{{ item.id }}/enrollments"', template)
        self.assertIn("新增报名记录", template)
        self.assertIn('data-validity-range', template)
        self.assertNotIn('enrollments/new', template)
        form_script = (Path(__file__).parents[1] / "app/static/admin-form.js").read_text(encoding="utf-8")
        self.assertIn("hasAttribute('formaction')", form_script)

    def test_create_student_saves_note_service_and_dates(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)
        campus = models.Campus(name="中心店", address="测试地址", phone="13800138000")
        db.add(campus)
        db.commit()

        class Request:
            state = SimpleNamespace(admin_identity=AdminIdentity(None, "admin", "管理员", ROLE_ADMIN))

            async def form(self):
                return {
                    "name": "测试学生", "grade": "四年级", "campus_id": campus.id,
                    "service_type": "自习室场地服务", "started_on": "2026-11-24",
                    "ended_on": "2026-12-23", "status": "active",
                    "note": "花生过敏，需家长接送",
                }

        asyncio.run(create_student(Request(), db))
        student = db.query(models.Student).one()
        self.assertEqual(student.note, "花生过敏，需家长接送")
        self.assertEqual(student.enrollments[0].service_type, "自习室场地服务")
        self.assertEqual(student.enrollments[0].ended_on, date(2026, 12, 23))
        db.close()
        engine.dispose()

    def test_existing_database_gets_nullable_student_note(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE students (id VARCHAR(32) PRIMARY KEY, name VARCHAR(80))"))
        _ensure_schema_compatibility(engine)
        columns = {column["name"]: column for column in inspect(engine).get_columns("students")}
        self.assertIn("note", columns)
        self.assertTrue(columns["note"]["nullable"])
        engine.dispose()

    def test_enrollment_fee_fields_are_nullable_and_rendered(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)
        campus = models.Campus(name="中心店", address="测试地址", phone="13800138000")
        student = models.Student(name="学生", grade="四年级")
        db.add_all([campus, student])
        db.flush()
        enrollment = models.StudentEnrollment(
            student_id=student.id, campus_id=campus.id, service_type="自习室场地服务",
            receivable_amount=Decimal("1999.00"), received_amount=Decimal("1500.00"),
        )
        db.add(enrollment)
        db.commit()
        self.assertEqual(enrollment.receivable_amount, Decimal("1999.00"))
        self.assertIsNone(models.StudentEnrollment(student_id=student.id, campus_id=campus.id, service_type="旧").received_amount)
        template = (Path(__file__).parents[1] / "app/templates/student_detail.html").read_text(encoding="utf-8")
        self.assertIn('name="receivable_amount"', template)
        self.assertIn('name="received_amount"', template)
        db.close()
        engine.dispose()
