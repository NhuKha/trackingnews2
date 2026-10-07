import hashlib
import hmac

from app.config import settings

COOKIE_NAME = "stock_signal_session"


def auth_enabled() -> bool:
    return bool(settings.app_password)


def expected_token() -> str:
    password = settings.app_password or ""
    return hmac.new(
        settings.app_secret.encode("utf-8"),
        password.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def valid_token(token: str | None) -> bool:
    if not auth_enabled():
        return True
    if not token:
        return False
    return hmac.compare_digest(token, expected_token())
