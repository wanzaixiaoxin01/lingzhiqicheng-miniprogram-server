import unittest

from app.domain.materials import (
    MAX_MATERIAL_SIZE,
    build_storage_name,
    validate_material_file,
)


class MaterialFileRulesTest(unittest.TestCase):
    def test_accepts_documents_archives_and_images(self):
        for filename in ("guide.docx", "scores.xlsx", "materials.zip", "notice.pdf", "cover.png"):
            info = validate_material_file(filename, 1024)
            self.assertEqual(info.original_name, filename)
            self.assertGreater(info.content_type, "")

    def test_rejects_executable_files(self):
        with self.assertRaises(ValueError):
            validate_material_file("installer.exe", 1024)

    def test_rejects_files_over_the_upload_limit(self):
        with self.assertRaises(ValueError):
            validate_material_file("materials.zip", MAX_MATERIAL_SIZE + 1)

    def test_marks_office_documents_previewable_but_zip_download_only(self):
        self.assertTrue(validate_material_file("lesson.docx", 1024).can_preview)
        self.assertTrue(validate_material_file("lesson.xlsx", 1024).can_preview)
        self.assertFalse(validate_material_file("lesson.zip", 1024).can_preview)
        self.assertFalse(validate_material_file("readme.txt", 1024).can_preview)

    def test_storage_name_does_not_use_the_original_filename(self):
        self.assertEqual(build_storage_name("material-123", "../课程资料.DOCX"), "material-123.docx")


if __name__ == "__main__":
    unittest.main()
