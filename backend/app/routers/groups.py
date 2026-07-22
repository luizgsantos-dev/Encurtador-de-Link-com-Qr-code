import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Group, User
from app.schemas import GroupCreate, GroupOut, GroupUpdate
from app.security import get_current_user, require_admin

router = APIRouter(prefix="/api/groups", tags=["groups"])


async def _get_group_or_404(group_id: uuid.UUID, db: AsyncSession) -> Group:
    group = await db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo não encontrado")
    return group


@router.get("", response_model=list[GroupOut])
async def list_groups(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if user.is_admin:
        result = await db.execute(select(Group).order_by(Group.name))
        return result.scalars().all()
    return sorted(user.groups, key=lambda group: group.name)


@router.post(
    "", response_model=GroupOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)]
)
async def create_group(payload: GroupCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(Group).where(Group.name == payload.name))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Grupo já existe")

    group = Group(name=payload.name)
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


@router.patch("/{group_id}", response_model=GroupOut, dependencies=[Depends(require_admin)])
async def update_group(group_id: uuid.UUID, payload: GroupUpdate, db: AsyncSession = Depends(get_db)):
    group = await _get_group_or_404(group_id, db)

    existing = await db.scalar(
        select(Group).where(Group.name == payload.name, Group.id != group_id)
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Grupo já existe")

    group.name = payload.name
    await db.commit()
    await db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
async def delete_group(group_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    group = await _get_group_or_404(group_id, db)
    await db.delete(group)
    await db.commit()
