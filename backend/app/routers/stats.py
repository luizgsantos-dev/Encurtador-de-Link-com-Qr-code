import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Click, Link, User
from app.schemas import DailyClicks, DashboardOverview, DeviceCount, LinkStats, ReferrerCount, TopLinkStat
from app.security import get_current_user

router = APIRouter(prefix="/api/links", tags=["stats"])
overview_router = APIRouter(prefix="/api/stats", tags=["stats"])

DAYS_WINDOW = 30
TOP_REFERRERS_LIMIT = 5
TOP_LINKS_LIMIT = 8


@router.get("/{link_id}/stats", response_model=LinkStats)
async def get_link_stats(
    link_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    link = await db.get(Link, link_id)
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link não encontrado")
    if not user.is_admin and (
        link.group_id is None or link.group_id not in {group.id for group in user.groups}
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link não encontrado")

    total_clicks = await db.scalar(select(func.count(Click.id)).where(Click.link_id == link_id))

    since = datetime.now(timezone.utc) - timedelta(days=DAYS_WINDOW)
    daily_result = await db.execute(
        select(func.date(Click.clicked_at).label("day"), func.count(Click.id))
        .where(Click.link_id == link_id, Click.clicked_at >= since)
        .group_by("day")
        .order_by("day")
    )
    daily_clicks = [
        DailyClicks(date=str(day), count=count) for day, count in daily_result.all()
    ]

    device_result = await db.execute(
        select(Click.device_type, func.count(Click.id))
        .where(Click.link_id == link_id)
        .group_by(Click.device_type)
    )
    device_breakdown = [
        DeviceCount(device_type=device_type, count=count)
        for device_type, count in device_result.all()
    ]

    referrer_result = await db.execute(
        select(func.coalesce(Click.referrer, "direto"), func.count(Click.id))
        .where(Click.link_id == link_id)
        .group_by(Click.referrer)
        .order_by(func.count(Click.id).desc())
        .limit(TOP_REFERRERS_LIMIT)
    )
    top_referrers = [
        ReferrerCount(referrer=referrer, count=count) for referrer, count in referrer_result.all()
    ]

    return LinkStats(
        total_clicks=total_clicks or 0,
        daily_clicks=daily_clicks,
        device_breakdown=device_breakdown,
        top_referrers=top_referrers,
    )


def _accessible_link_ids_subquery(user: User):
    query = select(Link.id)
    if not user.is_admin:
        query = query.where(Link.group_id.in_([g.id for g in user.groups]))
    return query


@overview_router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    if not user.is_admin and not user.groups:
        return DashboardOverview(
            daily_clicks_total=[], daily_clicks_partner=[], daily_clicks_general=[], top_links=[]
        )

    link_ids_subq = _accessible_link_ids_subquery(user)
    since = datetime.now(timezone.utc) - timedelta(days=DAYS_WINDOW)
    all_days = [(since + timedelta(days=i)).date().isoformat() for i in range(DAYS_WINDOW + 1)]

    async def _daily_series(extra_link_ids_subq=None) -> list[DailyClicks]:
        result = await db.execute(
            select(func.date(Click.clicked_at).label("day"), func.count(Click.id))
            .where(
                Click.link_id.in_(extra_link_ids_subq if extra_link_ids_subq is not None else link_ids_subq),
                Click.clicked_at >= since,
            )
            .group_by("day")
        )
        counts_by_day = {str(day): count for day, count in result.all()}
        return [DailyClicks(date=day, count=counts_by_day.get(day, 0)) for day in all_days]

    partner_link_ids_subq = select(Link.id).where(Link.id.in_(link_ids_subq), Link.partner_id.isnot(None))
    general_link_ids_subq = select(Link.id).where(Link.id.in_(link_ids_subq), Link.partner_id.is_(None))

    daily_clicks_total = await _daily_series()
    daily_clicks_partner = await _daily_series(partner_link_ids_subq)
    daily_clicks_general = await _daily_series(general_link_ids_subq)

    top_result = await db.execute(
        select(Link.id, Link.title, func.count(Click.id).label("total_clicks"))
        .join(Click, Click.link_id == Link.id)
        .where(Link.id.in_(link_ids_subq))
        .group_by(Link.id)
        .order_by(func.count(Click.id).desc())
        .limit(TOP_LINKS_LIMIT)
    )
    top_links = [
        TopLinkStat(id=link_id, title=title, total_clicks=total_clicks)
        for link_id, title, total_clicks in top_result.all()
    ]

    return DashboardOverview(
        daily_clicks_total=daily_clicks_total,
        daily_clicks_partner=daily_clicks_partner,
        daily_clicks_general=daily_clicks_general,
        top_links=top_links,
    )
