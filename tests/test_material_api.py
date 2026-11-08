import os
import unittest
from types import SimpleNamespace

os.environ["PUBLIC_BASE_URL"] = "https://api.example.test"

from app.routes.public_api import material_payload
from app.config import settings


class MaterialApiContractTest(unittest.TestCase):
    def test_material_payload_contains_download_metadata(self):
        settings.public_base_url = "https://api.example.test"
        material = SimpleNamespace(
            id="material-1",
            title="数学资料",
            summary="复习资料",
            original_name="math-guide.docx",
            extension=".docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size=2048,
            can_preview=True,
            download_count=3,
            sort_order=1,
            status="published",
        )

        payload = material_payload(material)

        self.assertEqual(payload["file_name"], "math-guide.docx")
        self.assertEqual(payload["file_size_label"], "2.0 KB")
        self.assertEqual(payload["download_url"], "https://api.example.test/api/public/materials/material-1/download")
        self.assertTrue(payload["can_preview"])
        self.assertNotIn("sort_order", payload)


if __name__ == "__main__":
    unittest.main()
