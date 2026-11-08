import unittest

from app.auth import parse_parent_session, parent_session_token, verify_credentials


class AdminAuthTest(unittest.TestCase):
    def test_accepts_configured_credentials(self):
        self.assertTrue(verify_credentials("admin", "secret", "admin", "secret"))

    def test_rejects_wrong_credentials(self):
        self.assertFalse(verify_credentials("admin", "wrong", "admin", "secret"))
        self.assertFalse(verify_credentials("other", "secret", "admin", "secret"))

    def test_parent_session_token_round_trip_rejects_tampering(self):
        token = parent_session_token("wx-parent")
        self.assertEqual(parse_parent_session(token), "wx-parent")
        self.assertIsNone(parse_parent_session(f"{token}tampered"))


if __name__ == "__main__":
    unittest.main()
