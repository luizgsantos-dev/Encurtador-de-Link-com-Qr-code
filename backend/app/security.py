import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, HTTPException, status
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

COOKIE_NAME = "access_token"


def verify_credentials(username: str, password: str) -> bool:
    valid_user = secrets.compare_digest(username, settings.admin_username)
    valid_pass = secrets.compare_digest(password, settings.admin_password)
    return valid_user and valid_pass


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        subject: str | None = payload.get("sub")
        if subject is None:
            raise JWTError("missing subject")
        return subject
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado"
        ) from exc


async def get_current_user(access_token: str | None = Cookie(default=None)) -> str:
    if access_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    return decode_access_token(access_token)
