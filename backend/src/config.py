import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BACKEND_DIR / "data" / "app.db"))
ASSETS_DIR = os.environ.get("ASSETS_DIR", str(BACKEND_DIR / "assets"))

COOKIE_NAME = os.environ.get("COOKIE_NAME", "session_uuid")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() in ("1", "true", "yes")
COOKIE_MAX_AGE_SECONDS = int(os.environ.get("COOKIE_MAX_AGE_SECONDS", str(60 * 60 * 24 * 365)))


def encode_uuid(uuid_bytes: bytes) -> str:
    return uuid_bytes.hex()


def decode_uuid(value: str) -> bytes | None:
    try:
        decoded = bytes.fromhex(value)
    except ValueError:
        return None
    if len(decoded) != 16:
        return None
    return decoded
