import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Click, Link
from app.schemas import LinkCreate, LinkOut, LinkUpdate
from app.security import get_current_user
from app.utils.qrcode_gen import generate_qrcode_png, generate_qrcode_svg
from app.utils.shortcode import generate_short_code

router = APIRouter(prefix="/api/links", tags=["links"], dependencies=[Depends(get_current_user)])
settings = get_settings()


def _to_link_out(link: Link, total_clicks: int) -> LinkOut:
    return LinkOut(
        id=link.id,
        short_code=link.short_code,
        destination_url=link.destination_url,
        title=link.title,
        is_active=link.is_active,
        created_at=link.created_at,
        updated_at=link.updated_at,
        total_clicks=total_clicks,
        short_url=f"{settings.base_url}/{link.short_code}",
    )


async def _generate_unique_code(db: AsyncSession) -> str:
    for _ in range(10):
        code = generate_short_code()
        existing = await db.scalar(select(Link).where(Link.short_code == code))
        if existing is None:
            return code
    raise HTTPException(status_code=500, detail="Não foi possível gerar um código único")


@router.get("", response_model=list[LinkOut])
async def list_links(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Link, func.count(Click.id).label("total_clicks"))
        .outerjoin(Click, Click.link_id == Link.id)
        .group_by(Link.id)
        .order_by(Link.created_at.desc())
    )
    return [_to_link_out(link, total_clicks) for link, total_clicks in result.all()]


@router.post("", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
async def create_link(payload: LinkCreate, db: AsyncSession = Depends(get_db)):
    if payload.custom_code:
        existing = await db.scalar(select(Link).where(Link.short_code == payload.custom_code))
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Código já está em uso")
        code = payload.custom_code
    else:
        code = await _generate_unique_code(db)

    link = Link(short_code=code, destination_url=payload.destination_url, title=payload.title)
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return _to_link_out(link, total_clicks=0)


async def _get_link_or_404(link_id: uuid.UUID, db: AsyncSession) -> Link:
    link = await db.get(Link, link_id)
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link não encontrado")
    return link


@router.get("/{link_id}", response_model=LinkOut)
async def get_link(link_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    link = await _get_link_or_404(link_id, db)
    total_clicks = await db.scalar(select(func.count(Click.id)).where(Click.link_id == link_id))
    return _to_link_out(link, total_clicks or 0)


@router.patch("/{link_id}", response_model=LinkOut)
async def update_link(link_id: uuid.UUID, payload: LinkUpdate, db: AsyncSession = Depends(get_db)):
    link = await _get_link_or_404(link_id, db)

    if payload.destination_url is not None:
        link.destination_url = payload.destination_url
    if payload.title is not None:
        link.title = payload.title
    if payload.is_active is not None:
        link.is_active = payload.is_active

    await db.commit()
    await db.refresh(link)

    total_clicks = await db.scalar(select(func.count(Click.id)).where(Click.link_id == link_id))
    return _to_link_out(link, total_clicks or 0)


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(link_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    link = await _get_link_or_404(link_id, db)
    await db.delete(link)
    await db.commit()


@router.get("/{link_id}/qrcode")
async def get_qrcode(
    link_id: uuid.UUID,
    format: str = Query(default="png", pattern="^(png|svg)$"),
    db: AsyncSession = Depends(get_db),
):
    link = await _get_link_or_404(link_id, db)
    short_url = f"{settings.base_url}/{link.short_code}"

    if format == "svg":
        content = generate_qrcode_svg(short_url)
        media_type = "image/svg+xml"
    else:
        content = generate_qrcode_png(short_url)
        media_type = "image/png"

    return Response(content=content, media_type=media_type)
