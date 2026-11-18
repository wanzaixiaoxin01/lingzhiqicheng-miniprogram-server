import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CourseDeploymentConfigTest(unittest.TestCase):
    def test_caddy_exposes_seeded_and_uploaded_course_covers(self):
        caddyfile = (ROOT / "deploy/Caddyfile").read_text(encoding="utf-8")

        self.assertIn("handle /static/courses/*", caddyfile)
        self.assertGreaterEqual(caddyfile.count("handle /uploads/courses/*"), 2)


if __name__ == "__main__":
    unittest.main()
