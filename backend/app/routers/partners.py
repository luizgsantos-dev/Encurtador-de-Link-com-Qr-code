import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Click, Link, Partner
from app.schemas import (
    DailyClicks,
    PartnerCreate,
    PartnerLinkStat,
    PartnerOut,
    PartnerStats,
    PartnerUpdate,
)
from app.security import require_admin
from app.utils.urls import build_short_url

router = APIRouter(prefix="/api/partners", tags=["partners"], dependencies=[Depends(require_admin)])

DAYS_WINDOW = 30


def _to_partner_out(partner: Partner, total_links: int, total_clicks: int) -> PartnerOut:
    return PartnerOut(
        id=partner.id,
        name=partner.name,
        social_media=partner.social_media,
        email=partner.email,
        phone=partner.phone,
        description=partner.description,
        partnership=partner.partnership,
        domain=partner.domain,
        is_active=partner.is_active,
        created_at=partner.created_at,
        total_links=total_links,
        total_clicks=total_clicks,
    )


async def _get_partner_or_404(partner_id: uuid.UUID, db: AsyncSession) -> Partner:
    partner = await db.get(Partner, partner_id)
    if partner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parceiro não encontrado")
    return partner


@router.get("", response_model=list[PartnerOut])
async def list_partners(db: AsyncSession = Depends(get_db)):
    query = (
        select(
            Partner,
            func.count(func.distinct(Link.id)).label("total_links"),
            func.count(Click.id).label("total_clicks"),
        )
        .outerjoin(Link, Link.partner_id == Partner.id)
        .outerjoin(Click, Click.link_id == Link.id)
        .group_by(Partner.id)
        .order_by(func.count(Click.id).desc(), Partner.name)
    )
    result = await db.execute(query)
    return [
        _to_partner_out(partner, total_links, total_clicks)
        for partner, total_links, total_clicks in result.all()
    ]


@router.post("", response_model=PartnerOut, status_code=status.HTTP_201_CREATED)
async def create_partner(payload: PartnerCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(Partner).where(Partner.name == payload.name))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Parceiro já existe")

    if payload.domain is not None:
        existing_domain = await db.scalar(select(Partner).where(Partner.domain == payload.domain))
        if existing_domain is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Domínio já está em uso")

    partner = Partner(
        name=payload.name,
        social_media=payload.social_media,
        email=payload.email,
        phone=payload.phone,
        description=payload.description,
        partnership=payload.partnership,
        domain=payload.domain,
    )
    db.add(partner)
    await db.commit()
    await db.refresh(partner)
    return _to_partner_out(partner, total_links=0, total_clicks=0)


@router.patch("/{partner_id}", response_model=PartnerOut)
async def update_partner(
    partner_id: uuid.UUID, payload: PartnerUpdate, db: AsyncSession = Depends(get_db)
):
    partner = await _get_partner_or_404(partner_id, db)

    if payload.name is not None:
        existing = await db.scalar(
            select(Partner).where(Partner.name == payload.name, Partner.id != partner_id)
        )
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Parceiro já existe")
        partner.name = payload.name
    if payload.social_media is not None:
        partner.social_media = payload.social_media
    if payload.email is not None:
        partner.email = payload.email
    if payload.phone is not None:
        partner.phone = payload.phone
    if payload.description is not None:
        partner.description = payload.description
    if payload.partnership is not None:
        partner.partnership = payload.partnership
    if payload.domain is not None:
        existing_domain = await db.scalar(
            select(Partner).where(Partner.domain == payload.domain, Partner.id != partner_id)
        )
        if existing_domain is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Domínio já está em uso")
        partner.domain = payload.domain
    elif payload.clear_domain:
        partner.domain = None
    if payload.is_active is not None:
        partner.is_active = payload.is_active

    await db.commit()
    await db.refresh(partner)

    total_links = await db.scalar(select(func.count(Link.id)).where(Link.partner_id == partner_id))
    total_clicks = await db.scalar(
        select(func.count(Click.id)).join(Link, Click.link_id == Link.id).where(Link.partner_id == partner_id)
    )
    return _to_partner_out(partner, total_links or 0, total_clicks or 0)


@router.delete("/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_partner(partner_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    partner = await _get_partner_or_404(partner_id, db)
    await db.delete(partner)
    await db.commit()


@router.get("/{partner_id}/stats", response_model=PartnerStats)
async def get_partner_stats(partner_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    partner = await _get_partner_or_404(partner_id, db)

    total_clicks = await db.scalar(
        select(func.count(Click.id)).join(Link, Click.link_id == Link.id).where(Link.partner_id == partner_id)
    )

    since = datetime.now(timezone.utc) - timedelta(days=DAYS_WINDOW)
    daily_result = await db.execute(
        select(func.date(Click.clicked_at).label("day"), func.count(Click.id))
        .join(Link, Click.link_id == Link.id)
        .where(Link.partner_id == partner_id, Click.clicked_at >= since)
        .group_by("day")
        .order_by("day")
    )
    daily_clicks = [DailyClicks(date=str(day), count=count) for day, count in daily_result.all()]

    links_result = await db.execute(
        select(Link, func.count(Click.id).label("total_clicks"))
        .outerjoin(Click, Click.link_id == Link.id)
        .where(Link.partner_id == partner_id)
        .group_by(Link.id)
        .order_by(func.count(Click.id).desc())
    )
    links = [
        PartnerLinkStat(
            id=link.id,
            title=link.title,
            short_code=link.short_code,
            short_url=build_short_url(link.short_code, partner.domain),
            total_clicks=link_total_clicks,
        )
        for link, link_total_clicks in links_result.all()
    ]

    return PartnerStats(total_clicks=total_clicks or 0, daily_clicks=daily_clicks, links=links)
