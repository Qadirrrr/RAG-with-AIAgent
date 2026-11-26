"""Password hashing and JWT helpers.

JWT_SECRET comes from the environment. When it is not set, a dev-only
fallback is used so the app still runs locally; set a long random secret
in production (see backend/.env.example).
"""
import os
import warnings
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def _jwt_secret() -> str:
    secret = settings.JWT_SECRET or os.environ.get("JWT_SECRET", "")
    if not secret:
        warnings.warn("JWT_SECRET is not set; using a dev-only fallback. Set JWT_SECRET in production.")
        return "dev-only-change-me-in-production"
    return secret


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, _jwt_secret(), algorithm=ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
