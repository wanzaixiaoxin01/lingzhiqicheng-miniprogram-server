import json
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import settings


class WechatPhoneError(RuntimeError):
    pass


_token_cache = {"value": "", "expires_at": 0.0}


def get_wechat_access_token(*, opener=urlopen) -> str:
    now = time.time()
    if _token_cache["value"] and _token_cache["expires_at"] > now + 60:
        return str(_token_cache["value"])
    if not settings.miniprogram_app_id or not settings.miniprogram_app_secret:
        raise WechatPhoneError("服务端尚未配置微信小程序凭据")

    query = urlencode({
        "grant_type": "client_credential",
        "appid": settings.miniprogram_app_id,
        "secret": settings.miniprogram_app_secret,
    })
    try:
        with opener(f"https://api.weixin.qq.com/cgi-bin/token?{query}", timeout=8) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        raise WechatPhoneError("微信手机号服务暂时不可用") from exc
    token = str(result.get("access_token") or "")
    if not token:
        raise WechatPhoneError(str(result.get("errmsg") or "获取微信接口凭证失败"))
    expires_in = int(result.get("expires_in") or 7200)
    _token_cache.update(value=token, expires_at=now + expires_in)
    return token


def exchange_phone_code(phone_code: str, *, access_token: str | None = None, opener=urlopen) -> str:
    code = (phone_code or "").strip()
    if not code:
        raise WechatPhoneError("缺少微信手机号授权凭证")
    token = access_token or get_wechat_access_token(opener=opener)
    request = Request(
        f"https://api.weixin.qq.com/wxa/business/getuserphonenumber?access_token={token}",
        data=json.dumps({"code": code}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener(request, timeout=8) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        raise WechatPhoneError("微信手机号服务暂时不可用") from exc
    phone = str((result.get("phone_info") or {}).get("phoneNumber") or "")
    if not phone:
        raise WechatPhoneError(str(result.get("errmsg") or "手机号授权失败"))
    return phone
