import json
import unittest

from app.services.wechat_phone import WechatPhoneError, exchange_phone_code


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class WechatPhoneTest(unittest.TestCase):
    def test_exchange_returns_wechat_verified_phone(self):
        requests = []

        def opener(request, timeout):
            requests.append((request, timeout))
            return FakeResponse({"phone_info": {"phoneNumber": "13811112222"}})

        phone = exchange_phone_code("phone-code", access_token="access-token", opener=opener)

        self.assertEqual(phone, "13811112222")
        self.assertIn("access_token=access-token", requests[0][0].full_url)
        self.assertEqual(json.loads(requests[0][0].data), {"code": "phone-code"})

    def test_exchange_rejects_wechat_error(self):
        def opener(request, timeout):
            return FakeResponse({"errcode": 40029, "errmsg": "invalid code"})

        with self.assertRaisesRegex(WechatPhoneError, "invalid code"):
            exchange_phone_code("bad-code", access_token="access-token", opener=opener)


if __name__ == "__main__":
    unittest.main()
