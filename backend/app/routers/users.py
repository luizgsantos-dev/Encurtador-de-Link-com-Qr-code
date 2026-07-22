import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Group, User
from app.schemas import UserCreate, UserOut, UserUpdate
from app.security import hash_password, require_admin

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(require_admin)])


async def _load_groups(db: AsyncSession, group_ids: list[uuid.UUID]) -> list[Group]:
    if not group_ids:
        return []
    result = await db.execute(select(Group).where(Group.id.in_(group_ids)))
    groups = result.scalars().all()
    if len(groups) != len(set(group_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Um ou mais grupos não existem"
        )
    return list(groups)


async def _get_user_or_404(user_id: uuid.UUID, db: AsyncSession) -> User:
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.groups))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return user


@router.get("", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).options(selectinload(User.groups)).order_by(User.created_at)
    )
    return result.scalars().all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.username == payload.username))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já existe")

    groups = await _load_groups(db, payload.group_ids)
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_admin=payload.is_admin,
        groups=groups,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user, attribute_names=["groups"])
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: uuid.UUID, payload: UserUpdate, db: AsyncSession = Depends(get_db)):
    user = await _get_user_or_404(user_id, db)

    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.group_ids is not None:
        user.groups = await _load_groups(db, payload.group_ids)

    await db.commit()
    await db.refresh(user, attribute_names=["groups"])
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_admin),
):
    if user_id == current.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Não é possível excluir o próprio usuário"
        )
    user = await _get_user_or_404(user_id, db)
    await db.delete(user)
    await db.commit()
