import unittest

from app.domain.course_images import validate_course_image


class InterestActivityImageTest(unittest.TestCase):
    def test_accepts_web_images_within_ten_megabytes(self):
        self.assertEqual(validate_course_image("activity.jpg", 1024).extension, ".jpg")
        self.assertEqual(validate_course_image("activity.webp", 1024).extension, ".webp")

    def test_rejects_invalid_or_oversized_images(self):
        with self.assertRaises(ValueError):
            validate_course_image("activity.pdf", 100)
        with self.assertRaises(ValueError):
            validate_course_image("activity.png", 11 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
