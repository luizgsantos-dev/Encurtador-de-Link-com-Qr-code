import logging
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.models import Click, Link, User
from app.schemas import FunnelOut, FunnelRow
from app.security import get_current_user
from app.utils.urls import build_short_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stats", tags=["funnel"])

# view criada no Vivart_BI (sql/vw_funil_links_acessos.sql): um acesso do site por
# linha, já atribuído ao link curto e com a etapa atual do lead no CRM (etapa_rank)
FUNNEL_SQL = """
    SELECT short_code,
           count(*)                                  AS accesses,
           count(*) FILTER (WHERE etapa_rank >= 1)   AS leads,
           count(*) FILTER (WHERE etapa_rank >= 2)   AS appointments,
           count(*) FILTER (WHERE etapa_rank >= 3)   AS visits,
           count(*) FILTER (WHERE etapa_rank >= 4)   AS sales
    FROM vw_funil_links_acessos
    WHERE short_code = ANY(:codes)
      AND (CAST(:start AS timestamp) IS NULL OR created_at >= :start)
      AND (CAST(:end AS timestamp) IS NULL OR created_at < :end)
    GROUP BY short_code
"""

_external_engine: AsyncEngine | None = None


def _get_external_engine() -> AsyncEngine | None:
    global _external_engine
    settings = get_settings()
    if not settings.external_db_url:
        return None
    if _external_engine is None:
        _external_engine = create_async_engine(
            settings.external_db_url, pool_pre_ping=True, pool_size=2, max_overflow=2
        )
    return _external_engine


@router.get("/funnel", response_model=FunnelOut)
async def get_funnel(
    start: date | None = Query(None),
    end: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.is_admin and not user.groups:
        return FunnelOut(rows=[], crm_available=True)

    links_query = select(Link).options(selectinload(Link.partner)).order_by(Link.title)
    if not user.is_admin:
        links_query = links_query.where(Link.group_id.in_([g.id for g in user.groups]))
    links = (await db.scalars(links_query)).all()
    if not links:
        return FunnelOut(rows=[], crm_available=True)

    # limites do período: início inclusivo, fim inclusivo (vira < dia seguinte)
    start_dt = datetime.combine(start, time.min) if start else None
    end_dt = datetime.combine(end + timedelta(days=1), time.min) if end else None

    clicks_query = (
        select(Click.link_id, func.count(Click.id))
        .where(Click.link_id.in_([link.id for link in links]))
        .group_by(Click.link_id)
    )
    if start_dt:
        clicks_query = clicks_query.where(Click.clicked_at >= start_dt.replace(tzinfo=timezone.utc))
    if end_dt:
        clicks_query = clicks_query.where(Click.clicked_at < end_dt.replace(tzinfo=timezone.utc))
    clicks_by_link = dict((await db.execute(clicks_query)).all())

    crm_by_code: dict[str, dict] = {}
    crm_available, crm_error = True, None
    engine = _get_external_engine()
    if engine is None:
        crm_available, crm_error = False, "Banco do CRM (EXTERNAL_DB_URL) não configurado"
    else:
        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(FUNNEL_SQL),
                    {"codes": [link.short_code for link in links], "start": start_dt, "end": end_dt},
                )
                crm_by_code = {row.short_code: row._mapping for row in result}
        except Exception:
            logger.exception("Falha ao consultar o funil no banco do CRM")
            crm_available, crm_error = False, "Não foi possível consultar o banco do CRM"

    rows = []
    for link in links:
        crm = crm_by_code.get(link.short_code, {})
        rows.append(
            FunnelRow(
                link_id=link.id,
                short_code=link.short_code,
                title=link.title,
                short_url=build_short_url(link.short_code, link.partner.domain if link.partner else None),
                name=link.utm_medium or (link.partner.name if link.partner else None),
                utm_source=link.utm_source,
                clicks=clicks_by_link.get(link.id, 0),
                accesses=crm.get("accesses", 0),
                leads=crm.get("leads", 0),
                appointments=crm.get("appointments", 0),
                visits=crm.get("visits", 0),
                sales=crm.get("sales", 0),
            )
        )
    return FunnelOut(rows=rows, crm_available=crm_available, crm_error=crm_error)
