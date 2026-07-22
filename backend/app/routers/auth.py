from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, MeOut
from app.security import COOKIE_NAME, create_access_token, get_current_user, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/login")
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.username == payload.username).options(selectinload(User.groups))
    )
    user = result.scalar_one_or_none()

    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    token = create_access_token(subject=str(user.id))
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )
    return {"message": "login realizado com sucesso"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"message": "logout realizado com sucesso"}


@router.get("/me", response_model=MeOut)
async def me(user: User = Depends(get_current_user)):
    return user
