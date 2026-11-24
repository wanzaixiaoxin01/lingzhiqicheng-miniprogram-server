import unittest
from datetime import date
from fastapi import HTTPException
from app.domain.parent_dashboard import validity_label
from app.routes.operations_admin import student_validity_dates


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
