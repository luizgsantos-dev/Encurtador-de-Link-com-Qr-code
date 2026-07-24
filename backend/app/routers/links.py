import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Click, Group, Link, Partner, User
from app.schemas import LinkCreate, LinkOut, LinkUpdate
from app.security import get_current_user
from app.utils.qrcode_gen import generate_qrcode_png, generate_qrcode_svg
from app.utils.shortcode import generate_short_code
from app.utils.urls import build_short_url

router = APIRouter(prefix="/api/links", tags=["links"])


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
        short_url=build_short_url(link.short_code, link.partner.domain if link.partner else None),
        group_id=link.group_id,
        group_name=link.group.name if link.group else None,
        partner_id=link.partner_id,
        partner_name=link.partner.name if link.partner else None,
        utm_campaign=link.utm_campaign,
        utm_source=link.utm_source,
        utm_medium=link.utm_medium,
        utm_term=link.utm_term,
    )


async def _resolve_partner(partner_id: uuid.UUID, db: AsyncSession) -> Partner:
    partner = await db.get(Partner, partner_id)
    if partner is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parceiro não encontrado")
    return partner


def _check_link_access(user: User, link: Link) -> None:
    if user.is_admin:
        return
    if link.group_id is None or link.group_id not in {group.id for group in user.groups}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link não encontrado")


async def _ensure_group_access(user: User, group_id: uuid.UUID, db: AsyncSession) -> Group:
    group = await db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grupo não encontrado")
    if not user.is_admin and group_id not in {g.id for g in user.groups}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso a este grupo")
    return group


async def _generate_unique_code(db: AsyncSession) -> str:
    for _ in range(10):
        code = generate_short_code()
        existing = await db.scalar(select(Link).where(Link.short_code == code))
        if existing is None:
            return code
    raise HTTPException(status_code=500, detail="Não foi possível gerar um código único")


async def _get_link_or_404(link_id: uuid.UUID, db: AsyncSession) -> Link:
    result = await db.execute(
        select(Link)
        .where(Link.id == link_id)
        .options(selectinload(Link.group), selectinload(Link.partner))
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link não encontrado")
    return link


@router.get("", response_model=list[LinkOut])
async def list_links(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if not user.is_admin and not user.groups:
        return []

    query = (
        select(Link, func.count(Click.id).label("total_clicks"))
        .outerjoin(Click, Click.link_id == Link.id)
        .group_by(Link.id)
        .order_by(Link.created_at.desc())
        .options(selectinload(Link.group), selectinload(Link.partner))
    )
    if not user.is_admin:
        query = query.where(Link.group_id.in_([group.id for group in user.groups]))

    result = await db.execute(query)
    return [_to_link_out(link, total_clicks) for link, total_clicks in result.all()]


@router.post("", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
async def create_link(
    payload: LinkCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    group = await _ensure_group_access(user, payload.group_id, db)
    partner = await _resolve_partner(payload.partner_id, db) if payload.partner_id else None

    if payload.custom_code:
        existing = await db.scalar(select(Link).where(Link.short_code == payload.custom_code))
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Código já está em uso")
        code = payload.custom_code
    else:
        code = await _generate_unique_code(db)

    link = Link(
        short_code=code,
        destination_url=payload.destination_url,
        title=payload.title,
        group_id=group.id,
        partner_id=partner.id if partner else None,
        utm_campaign=payload.utm_campaign,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_term=payload.utm_term,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link, attribute_names=["created_at", "updated_at"])
    link.group = group
    link.partner = partner
    return _to_link_out(link, total_clicks=0)


@router.get("/{link_id}", response_model=LinkOut)
async def get_link(
    link_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    link = await _get_link_or_404(link_id, db)
    _check_link_access(user, link)
    total_clicks = await db.scalar(select(func.count(Click.id)).where(Click.link_id == link_id))
    return _to_link_out(link, total_clicks or 0)


@router.patch("/{link_id}", response_model=LinkOut)
async def update_link(
    link_id: uuid.UUID,
    payload: LinkUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    link = await _get_link_or_404(link_id, db)
    _check_link_access(user, link)

    has_utm_in_payload = any(
        [payload.utm_campaign, payload.utm_source, payload.utm_medium, payload.utm_term]
    )
    if payload.clear_partner and has_utm_in_payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Não é possível definir UTM ao remover o parceiro do link",
        )
    final_partner_id = payload.partner_id if payload.partner_id is not None else (
        None if payload.clear_partner else link.partner_id
    )
    if final_partner_id is None and has_utm_in_payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="UTM estruturado requer um link vinculado a um parceiro",
        )

    if payload.destination_url is not None:
        link.destination_url = payload.destination_url
    if payload.title is not None:
        link.title = payload.title
    if payload.is_active is not None:
        link.is_active = payload.is_active
    if payload.group_id is not None:
        group = await _ensure_group_access(user, payload.group_id, db)
        link.group_id = group.id
        link.group = group
    if payload.partner_id is not None:
        partner = await _resolve_partner(payload.partner_id, db)
        link.partner_id = partner.id
        link.partner = partner
    elif payload.clear_partner:
        link.partner_id = None
        link.partner = None
        link.utm_campaign = None
        link.utm_source = None
        link.utm_medium = None
        link.utm_term = None
    if payload.utm_campaign is not None:
        link.utm_campaign = payload.utm_campaign
    if payload.utm_source is not None:
        link.utm_source = payload.utm_source
    if payload.utm_medium is not None:
        link.utm_medium = payload.utm_medium
    if payload.utm_term is not None:
        link.utm_term = payload.utm_term

    await db.commit()
    await db.refresh(link, attribute_names=["updated_at"])

    total_clicks = await db.scalar(select(func.count(Click.id)).where(Click.link_id == link_id))
    return _to_link_out(link, total_clicks or 0)


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    link_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    link = await _get_link_or_404(link_id, db)
    _check_link_access(user, link)
    await db.delete(link)
    await db.commit()


@router.get("/{link_id}/qrcode")
async def get_qrcode(
    link_id: uuid.UUID,
    format: str = Query(default="png", pattern="^(png|svg)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    link = await _get_link_or_404(link_id, db)
    _check_link_access(user, link)
    short_url = build_short_url(link.short_code, link.partner.domain if link.partner else None)

    if format == "svg":
        content = generate_qrcode_svg(short_url)
        media_type = "image/svg+xml"
    else:
        content = generate_qrcode_png(short_url)
        media_type = "image/png"

    return Response(content=content, media_type=media_type)
