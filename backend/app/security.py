import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models import User

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

COOKIE_NAME = "access_token"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


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


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if access_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")

    subject = decode_access_token(access_token)
    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado"
        ) from exc

    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.groups))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores"
        )
    return user
