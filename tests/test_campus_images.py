import unittest

from app.domain.campus_images import build_campus_storage_name, validate_campus_image


class CampusImageRulesTest(unittest.TestCase):
    def test_accepts_supported_cover_images(self):
        info = validate_campus_image("lianhua-store.webp", 2 * 1024 * 1024)

        self.assertEqual(info.extension, ".webp")
        self.assertEqual(info.content_type, "image/webp")
        self.assertEqual(build_campus_storage_name("1", info.extension), "campus-1.webp")

    def test_rejects_non_image_and_oversized_files(self):
        with self.assertRaises(ValueError):
            validate_campus_image("campus.pdf", 100)
        with self.assertRaises(ValueError):
            validate_campus_image("campus.jpg", 11 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
