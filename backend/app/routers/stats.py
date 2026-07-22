import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Click, Link
from app.schemas import DailyClicks, DeviceCount, LinkStats, ReferrerCount
from app.security import get_current_user

router = APIRouter(prefix="/api/links", tags=["stats"], dependencies=[Depends(get_current_user)])

DAYS_WINDOW = 30
TOP_REFERRERS_LIMIT = 5


@router.get("/{link_id}/stats", response_model=LinkStats)
async def get_link_stats(link_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    link = await db.get(Link, link_id)
    if link is None:
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
