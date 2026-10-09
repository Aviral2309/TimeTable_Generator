from __future__ import annotations
import base64
import hashlib
import hmac
import json
import os
import time
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import User

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, salt_text, expected_text = encoded.split("$", 2)
        salt = base64.urlsafe_b64decode(salt_text)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
        return hmac.compare_digest(base64.urlsafe_b64encode(actual).decode(), expected_text)
    except (ValueError, TypeError):
        return False


def create_token(user: User, lifetime_seconds: int = 8 * 60 * 60) -> str:
    payload = {"sub": user.id, "role": user.role, "exp": int(time.time()) + lifetime_seconds}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(get_settings().secret_key.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def decode_token(token: str) -> dict:
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(get_settings().secret_key.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected): raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if payload["exp"] < time.time(): raise ValueError
        return payload
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(401, "Invalid or expired access token") from exc


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials: raise HTTPException(401, "Authentication required")
    payload = decode_token(credentials.credentials)
    user = db.scalar(select(User).where(User.id == payload["sub"], User.active.is_(True)))
    if not user: raise HTTPException(401, "User is inactive or missing")
    return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles: raise HTTPException(403, f"Requires one of these roles: {', '.join(roles)}")
        return user
    return dependency

