import base64
import getpass
import hashlib
import hmac
import os
import secrets
import time

COOKIE_NAME = "qx_session"
TTL_S = 12 * 3600
ITERATIONS = 210_000
MAX_ATTEMPTS = 5
WINDOW_S = 300

_attempts: dict[str, list[float]] = {}


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def login_configured() -> bool:
    names = ("DASHBOARD_ADMIN_USER", "DASHBOARD_ADMIN_PASSWORD_HASH", "DASHBOARD_SESSION_SECRET")
    return all(_env(n) for n in names)


def cookie_secure() -> bool:
    return os.getenv("DASHBOARD_COOKIE_SECURE", "1") != "0"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(candidate, bytes.fromhex(hash_hex))
    except (ValueError, AttributeError):
        return False


def check_credentials(username: str, password: str) -> bool:
    if not login_configured():
        return False
    user_ok = hmac.compare_digest(username, _env("DASHBOARD_ADMIN_USER"))
    return verify_password(password, _env("DASHBOARD_ADMIN_PASSWORD_HASH")) and user_ok


def is_rate_limited(ip: str) -> bool:
    now = time.time()
    recent = [t for t in _attempts.get(ip, []) if now - t < WINDOW_S]
    _attempts[ip] = recent
    return len(recent) >= MAX_ATTEMPTS


def record_failure(ip: str) -> None:
    _attempts.setdefault(ip, []).append(time.time())


def clear_failures(ip: str) -> None:
    _attempts.pop(ip, None)


def _sign(payload: bytes) -> bytes:
    return hmac.new(_env("DASHBOARD_SESSION_SECRET").encode(), payload, hashlib.sha256).digest()


def create_token(username: str) -> str:
    payload = f"{username}|{int(time.time()) + TTL_S}".encode()
    return f"{_b64(payload)}.{_b64(_sign(payload))}"


def verify_token(token: str | None) -> bool:
    if not token or not _env("DASHBOARD_SESSION_SECRET"):
        return False
    try:
        payload_b64, sig_b64 = token.split(".")
        payload, sig = _unb64(payload_b64), _unb64(sig_b64)
        username, expiry = payload.decode().split("|")
        if not hmac.compare_digest(sig, _sign(payload)) or time.time() > int(expiry):
            return False
    except ValueError:
        return False
    return hmac.compare_digest(username, _env("DASHBOARD_ADMIN_USER"))


if __name__ == "__main__":
    print(hash_password(getpass.getpass("Password: ")))
