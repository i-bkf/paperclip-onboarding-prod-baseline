from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from typing import Any

PBKDF2_ITERATIONS = 150_000


class TokenError(ValueError):
    pass


def _urlsafe_b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _urlsafe_b64decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if not password:
        raise ValueError("password must not be empty")
    local_salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), local_salt, PBKDF2_ITERATIONS
    )
    return (
        f"pbkdf2_sha256${PBKDF2_ITERATIONS}$"
        f"{_urlsafe_b64encode(local_salt)}${_urlsafe_b64encode(digest)}"
    )


def verify_password(password: str, encoded_password: str) -> bool:
    try:
        algorithm, rounds, salt_b64, digest_b64 = encoded_password.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    try:
        rounds_int = int(rounds)
        salt = _urlsafe_b64decode(salt_b64)
        expected_digest = _urlsafe_b64decode(digest_b64)
    except (TypeError, ValueError):
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, rounds_int
    )
    return hmac.compare_digest(digest, expected_digest)


def create_access_token(
    payload: dict[str, Any],
    *,
    secret: str,
    ttl_seconds: int,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(timezone.utc)
    body = {
        **payload,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(seconds=ttl_seconds)).timestamp()),
    }

    header_segment = _urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8")
    )
    payload_segment = _urlsafe_b64encode(
        json.dumps(body, separators=(",", ":")).encode("utf-8")
    )

    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()

    return f"{header_segment}.{payload_segment}.{_urlsafe_b64encode(signature)}"


def decode_access_token(token: str, *, secret: str, now: datetime | None = None) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenError("token must have 3 segments")

    header_segment, payload_segment, signature_segment = parts
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")

    expected_signature = hmac.new(
        secret.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()

    try:
        actual_signature = _urlsafe_b64decode(signature_segment)
    except (TypeError, ValueError) as exc:
        raise TokenError("token signature is invalid") from exc

    if not hmac.compare_digest(expected_signature, actual_signature):
        raise TokenError("token signature mismatch")

    try:
        header = json.loads(_urlsafe_b64decode(header_segment).decode("utf-8"))
        payload = json.loads(_urlsafe_b64decode(payload_segment).decode("utf-8"))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise TokenError("token is malformed") from exc

    if header.get("alg") != "HS256":
        raise TokenError("unsupported token algorithm")

    current_time = int((now or datetime.now(timezone.utc)).timestamp())
    if current_time >= int(payload.get("exp", 0)):
        raise TokenError("token expired")

    return payload
