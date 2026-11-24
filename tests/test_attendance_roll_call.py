import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app import models, repositories
from app.db import Base, _ensure_schema_compatibility
from app.routes.operations_admin import templates


class AttendanceRollCallTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.campus = models.Campus(
            id="campus-a",
            name="北舞渡服务点",
            address="漯河市舞阳县",
            phone="4009006368",
        )
        self.other_campus = models.Campus(
            id="campus-b",
            name="莲花服务点",
            address="漯河市舞阳县",
            phone="4009006368",
        )
        self.db.add_all([self.campus, self.other_campus])
        for index in range(12):
            student = models.Student(
                id=f"student-{index:02d}",
                name=f"学生{index:02d}",
                grade="小学四年级",
                school="北舞渡小学",
                guardian_name=f"家长{index:02d}",
                guardian_phone=f"1381234{index:04d}",
                status="active",
                created_at=datetime(2026, 1, 1) + timedelta(days=index),
            )
            self.db.add(student)
            self.db.add(
                models.StudentEnrollment(
                    id=f"enrollment-{index:02d}",
                    student_id=student.id,
                    campus_id=self.campus.id,
                    service_type="智习室学习",
                    status="active",
                    started_on=date(2026, 1, 1),
                    ended_on=date(2026, 12, 31),
                )
            )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_persists_morning_and_afternoon_flags(self):
        record = models.AttendanceRecord(
            student_id="student-00",
            campus_id=self.campus.id,
            attendance_date=date(2026, 11, 16),
            service_type="智习室学习",
            morning_present=True,
            afternoon_present=False,
        )
        self.db.add(record)
        self.db.commit()
        self.db.expire_all()

        saved = self.db.get(models.AttendanceRecord, record.id)
        self.assertTrue(saved.morning_present)
        self.assertFalse(saved.afternoon_present)

    def test_roster_filters_paginates_and_merges_attendance(self):
        self.db.add(
            models.AttendanceRecord(
                student_id="student-11",
                campus_id=self.campus.id,
                attendance_date=date(2026, 11, 16),
                service_type="智习室学习",
                morning_present=True,
                afternoon_present=False,
            )
        )
        self.db.commit()

        page = repositories.list_roll_call_roster(
            self.db,
            self.campus.id,
            date(2026, 11, 16),
            page=1,
            page_size=10,
        )
        filtered = repositories.list_roll_call_roster(
            self.db,
            self.campus.id,
            date(2026, 11, 16),
            search="0011",
        )

        self.assertEqual((page.total, page.total_pages, len(page.items)), (12, 2, 10))
        self.assertEqual((page.expected_count, page.morning_count, page.afternoon_count), (12, 1, 0))
        self.assertEqual(filtered.items[0].student.id, "student-11")
        self.assertTrue(filtered.items[0].morning_present)
        self.assertFalse(filtered.items[0].afternoon_present)

    def test_roster_only_includes_enrollment_valid_on_selected_date(self):
        self.db.add_all([
            models.StudentEnrollment(
                id="future-enrollment",
                student_id="student-00",
                campus_id=self.campus.id,
                service_type="未来报名",
                status="active",
                started_on=date(2027, 1, 1),
                ended_on=date(2027, 12, 31),
            ),
        ])
        self.db.commit()
        roster = repositories.list_roll_call_roster(self.db, self.campus.id, date(2026, 11, 16))
        self.assertEqual(roster.total, 12)
        self.assertEqual({item.enrollment.service_type for item in roster.items}, {"智习室学习"})

    def test_check_in_is_idempotent_and_removes_empty_record(self):
        first = repositories.set_roll_call_attendance(
            self.db,
            student_id="student-00",
            campus_id=self.campus.id,
            attendance_date=date(2026, 11, 16),
            period="afternoon",
            present=True,
            recorded_by=None,
        )
        repeated = repositories.set_roll_call_attendance(
            self.db,
            student_id="student-00",
            campus_id=self.campus.id,
            attendance_date=date(2026, 11, 16),
            period="afternoon",
            present=True,
            recorded_by=None,
        )

        self.assertEqual(first.id, repeated.id)
        self.assertFalse(repeated.morning_present)
        self.assertTrue(repeated.afternoon_present)
        self.assertEqual(self.db.query(models.AttendanceRecord).count(), 1)

        result = repositories.set_roll_call_attendance(
            self.db,
            student_id="student-00",
            campus_id=self.campus.id,
            attendance_date=date(2026, 11, 16),
            period="afternoon",
            present=False,
            recorded_by=None,
        )
        self.assertIsNone(result)
        self.assertEqual(self.db.query(models.AttendanceRecord).count(), 0)

    def test_check_in_rejects_invalid_period_and_missing_enrollment(self):
        with self.assertRaisesRegex(ValueError, "无效的点名时段"):
            repositories.set_roll_call_attendance(
                self.db,
                student_id="student-00",
                campus_id=self.campus.id,
                attendance_date=date(2026, 11, 16),
                period="evening",
                present=True,
                recorded_by=None,
            )
        with self.assertRaisesRegex(ValueError, "学生没有该网点的有效报名"):
            repositories.set_roll_call_attendance(
                self.db,
                student_id="student-00",
                campus_id=self.other_campus.id,
                attendance_date=date(2026, 11, 16),
                period="morning",
                present=True,
                recorded_by=None,
            )


class AttendanceCompatibilityMigrationTest(unittest.TestCase):
    def test_legacy_records_become_full_day_attendance(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE attendance_records (id VARCHAR(32) PRIMARY KEY)"))
            connection.execute(text("INSERT INTO attendance_records (id) VALUES ('legacy')"))

        _ensure_schema_compatibility(engine)

        columns = {item["name"] for item in inspect(engine).get_columns("attendance_records")}
        with engine.connect() as connection:
            row = connection.execute(
                text("SELECT morning_present, afternoon_present FROM attendance_records WHERE id = 'legacy'")
            ).mappings().one()
        self.assertIn("morning_present", columns)
        self.assertIn("afternoon_present", columns)
        self.assertTrue(row["morning_present"])
        self.assertTrue(row["afternoon_present"])
        engine.dispose()


class AttendanceRollCallPresentationTest(unittest.TestCase):
    def test_card_template_contains_guardian_and_two_check_in_controls(self):
        student = models.Student(
            id="student",
            name="张小明",
            grade="七年级",
            school="北舞渡中学",
            guardian_name="张女士",
            guardian_phone="13811112222",
            status="active",
        )
        enrollment = models.StudentEnrollment(
            id="enrollment",
            student_id=student.id,
            campus_id="campus",
            service_type="智习室学习",
            status="active",
        )
        item = repositories.RollCallItem(student, enrollment, False, True)

        template = templates.env.get_template("attendance_roll_call.html")
        html = template.render(
            resource="visits",
            items=[item],
            campuses=[models.Campus(id="campus", name="北舞渡服务点", address="漯河市", phone="4009006368")],
            selected_campus_id="campus",
            selected_date="2026-11-16",
            search="",
            expected_count=1,
            morning_count=0,
            afternoon_count=1,
            full_day_count=0,
            pagination={"page": 1, "total_pages": 1, "total": 1},
            page_urls=[],
            previous_url=None,
            next_url=None,
            admin_role="admin",
            section="visits",
        )

        self.assertIn('class="student-card"', html)
        self.assertIn("张女士", html)
        self.assertIn("上午签到", html)
        self.assertIn("下午已签", html)
        self.assertNotIn(">新增<", html)


if __name__ == "__main__":
    unittest.main()
