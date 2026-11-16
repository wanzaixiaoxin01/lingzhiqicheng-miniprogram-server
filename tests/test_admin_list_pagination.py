import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models, repositories
from app.db import Base


class AdminListPaginationTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_generic_resource_search_status_and_ten_item_pages(self):
        for index in range(12):
            self.db.add(
                models.Campus(
                    id=f"campus-{index:02d}",
                    name=f"测试网点 {index:02d}",
                    address="漯河市郾城区" if index < 11 else "舞阳县",
                    phone=f"1380000{index:04d}",
                    status="published" if index != 0 else "draft",
                    created_at=datetime(2026, 1, 1) + timedelta(days=index),
                )
            )
        self.db.commit()

        first_page = repositories.list_admin_items(models.Campus, self.db, page=1, page_size=10)
        second_page = repositories.list_admin_items(models.Campus, self.db, page=2, page_size=10)
        by_keyword = repositories.list_admin_items(models.Campus, self.db, search="舞阳")
        by_status = repositories.list_admin_items(models.Campus, self.db, status="draft")

        self.assertEqual((first_page.total, first_page.total_pages, len(first_page.items)), (12, 2, 10))
        self.assertEqual(len(second_page.items), 2)
        self.assertEqual(by_keyword.items[0].id, "campus-11")
        self.assertEqual(by_status.items[0].id, "campus-00")

    def test_student_list_supports_name_and_guardian_phone_search(self):
        campus = models.Campus(id="campus", name="莲花服务点", address="漯河市", phone="4009006368")
        self.db.add(campus)
        for index in range(12):
            student = models.Student(
                id=f"student-{index:02d}",
                name=f"学生{index:02d}",
                grade="小学四年级",
                guardian_name=f"家长{index:02d}",
                guardian_phone=f"1381234{index:04d}",
                status="active",
                created_at=datetime(2026, 1, 1) + timedelta(days=index),
            )
            self.db.add(student)
            self.db.add(
                models.StudentEnrollment(
                    student_id=student.id,
                    campus_id=campus.id,
                    service_type="智习室学习",
                    status="active",
                )
            )
        self.db.commit()

        page = repositories.list_scoped_students_page(self.db, [campus.id], page=1, page_size=10)
        by_name = repositories.list_scoped_students_page(self.db, [campus.id], search="学生11")
        by_phone = repositories.list_scoped_students_page(self.db, [campus.id], search="0011")

        self.assertEqual((page.total, page.total_pages, len(page.items)), (12, 2, 10))
        self.assertEqual(by_name.items[0].id, "student-11")
        self.assertEqual(by_phone.items[0].id, "student-11")

    def test_attendance_list_combines_keyword_date_and_scope(self):
        campus = models.Campus(id="campus", name="莲花服务点", address="漯河市", phone="4009006368")
        student = models.Student(id="student", name="张三", grade="初中一年级", status="active")
        self.db.add_all([campus, student])
        self.db.flush()
        for index in range(12):
            self.db.add(
                models.AttendanceRecord(
                    student_id=student.id,
                    campus_id=campus.id,
                    attendance_date=date(2026, 11, index + 1),
                    service_type="数学辅导" if index == 11 else "智习室学习",
                )
            )
        self.db.commit()

        page = repositories.list_scoped_attendance_page(self.db, [campus.id], page=1, page_size=10)
        filtered = repositories.list_scoped_attendance_page(
            self.db,
            [campus.id],
            search="数学",
            attendance_date=date(2026, 11, 12),
        )

        self.assertEqual((page.total, page.total_pages, len(page.items)), (12, 2, 10))
        self.assertEqual(filtered.total, 1)
        self.assertEqual(filtered.items[0].attendance_date, date(2026, 11, 12))


if __name__ == "__main__":
    unittest.main()
