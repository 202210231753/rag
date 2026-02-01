from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import timedelta
from typing import Any, Dict

from app.core.config import settings


class TokenError(ValueError):
    """令牌解析失败。"""


def hash_password(password: str, iterations: int = 260000) -> str:
    if not password:
        raise ValueError("密码不能为空")
    salt = secrets.token_urlsafe(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    digest = _b64url_encode(dk)
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(password: str, hashed: str) -> bool:
    if not password or not hashed:
        return False
    parts = hashed.split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    try:
        iterations = int(parts[1])
    except ValueError:
        return False
    salt = parts[2]
    expected = parts[3]
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    digest = _b64url_encode(dk)
    return hmac.compare_digest(digest, expected)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    if not settings.JWT_SECRET_KEY:
        raise TokenError("JWT_SECRET_KEY 未配置")
    now = int(time.time())
    expires = now + int((expires_delta or timedelta(minutes=60)).total_seconds())
    payload = {"sub": subject, "iat": now, "exp": expires}
    return _encode_jwt(payload, settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    if not token:
        raise TokenError("令牌为空")
    if not settings.JWT_SECRET_KEY:
        raise TokenError("JWT_SECRET_KEY 未配置")
    header, payload = _decode_jwt(token, settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)
    if header.get("alg") != settings.JWT_ALGORITHM:
        raise TokenError("算法不匹配")
    exp = payload.get("exp")
    if isinstance(exp, int) and exp < int(time.time()):
        raise TokenError("令牌已过期")
    return payload


def _encode_jwt(payload: Dict[str, Any], secret: str, algorithm: str) -> str:
    header = {"alg": algorithm, "typ": "JWT"}
    header_segment = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = _sign(signing_input, secret, algorithm)
    signature_segment = _b64url_encode(signature)
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def _decode_jwt(token: str, secret: str, algorithm: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenError("令牌结构错误")
    header_segment, payload_segment, signature_segment = parts
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = _b64url_decode(signature_segment)
    expected = _sign(signing_input, secret, algorithm)
    if not hmac.compare_digest(signature, expected):
        raise TokenError("签名校验失败")
    header = json.loads(_b64url_decode(header_segment).decode("utf-8"))
    payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
    return header, payload


def _sign(message: bytes, secret: str, algorithm: str) -> bytes:
    if algorithm != "HS256":
        raise TokenError("暂不支持的算法")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)
