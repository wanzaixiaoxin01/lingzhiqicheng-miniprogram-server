import unittest

from app.domain.leads import validate_lead_input


class LeadValidationTest(unittest.TestCase):
    def test_accepts_complete_trial_lead(self):
        result = validate_lead_input(
            {
                "name": " 王女士 ",
                "child_name": "小明",
                "phone": "13800138000",
                "child_age": 10,
                "child_grade": "小学四年级",
                "source": "trial",
                "campus_id": "campus-001",
                "appointment_at": "2099-01-01T14:30:00+08:00",
                "course_id": "course-001",
                "message": "周末方便到店体验",
            }
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.value["name"], "王女士")
        self.assertEqual(result.value["phone"], "13800138000")
        self.assertEqual(result.value["source"], "trial")

    def test_rejects_invalid_mobile_number(self):
        result = validate_lead_input(
            {
                "name": "王女士",
                "child_name": "小明",
                "phone": "12345",
                "child_age": 10,
                "child_grade": "小学四年级",
                "source": "trial",
                "campus_id": "campus-001",
                "appointment_at": "2099-01-01T14:30:00+08:00",
            }
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.errors, {"phone": "请输入有效的手机号"})

    def test_rejects_missing_required_fields(self):
        result = validate_lead_input(
            {
                "child_age": "",
                "name": " ",
                "phone": "13800138000",
                "child_grade": "",
                "source": " ",
                "campus_id": "campus-001",
                "appointment_at": "2099-01-01T14:30:00+08:00",
            }
        )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.errors,
            {
                "name": "请输入家长姓名",
                "source": "请选择预约来源",
            },
        )


if __name__ == "__main__":
    unittest.main()
