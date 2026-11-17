import unittest
from types import SimpleNamespace

from app.config import settings
from app.domain.poster_images import validate_poster_image
from app.routes.public_api import learning_machine_payload


class LearningMachinePosterTest(unittest.TestCase):
    def test_public_payload_uses_absolute_server_urls_and_keeps_order(self):
        settings.public_base_url = "https://miniapp.example.test"
        item = SimpleNamespace(
            value={
                "posters": [
                    {"id": "p2", "name": "第二张", "url": "/uploads/learning-machine/p2.jpg"},
                    {"id": "p1", "name": "第一张", "url": "https://cdn.example.test/p1.jpg"},
                ]
            }
        )

        payload = learning_machine_payload(item)

        self.assertEqual(
            [poster["url"] for poster in payload["posters"]],
            [
                "https://miniapp.example.test/uploads/learning-machine/p2.jpg",
                "https://cdn.example.test/p1.jpg",
            ],
        )
        self.assertEqual([poster["id"] for poster in payload["posters"]], ["p2", "p1"])

    def test_invalid_or_missing_config_returns_no_posters(self):
        self.assertEqual(learning_machine_payload(None), {"posters": []})
        self.assertEqual(learning_machine_payload(SimpleNamespace(value={"posters": "bad"})), {"posters": []})

    def test_poster_upload_only_accepts_web_images_within_limit(self):
        info = validate_poster_image("device.webp", 2 * 1024 * 1024)
        self.assertEqual(info.extension, ".webp")

        with self.assertRaises(ValueError):
            validate_poster_image("device.pdf", 100)
        with self.assertRaises(ValueError):
            validate_poster_image("device.jpg", 11 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
