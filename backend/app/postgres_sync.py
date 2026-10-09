import logging
import re
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.database import async_session_maker
from app.models import Click, Link, Partner
from app.utils.urls import build_short_url

logger = logging.getLogger(__name__)

_VALID_TABLE_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
    short_code VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255),
    destination_url TEXT,
    short_url TEXT,
    utm_campaign VARCHAR(255),
    utm_source VARCHAR(32),
    utm_medium VARCHAR(255),
    utm_term VARCHAR(32),
    total_clicks INTEGER NOT NULL DEFAULT 0,
    last_synced_at TIMESTAMPTZ NOT NULL
)
"""

UPSERT_SQL = """
INSERT INTO {table} (
    short_code, title, destination_url, short_url,
    utm_campaign, utm_source, utm_medium, utm_term,
    total_clicks, last_synced_at
)
VALUES (
    :short_code, :title, :destination_url, :short_url,
    :utm_campaign, :utm_source, :utm_medium, :utm_term,
    :total_clicks, :last_synced_at
)
ON CONFLICT (short_code) DO UPDATE SET
    title = EXCLUDED.title,
    destination_url = EXCLUDED.destination_url,
    short_url = EXCLUDED.short_url,
    utm_campaign = EXCLUDED.utm_campaign,
    utm_source = EXCLUDED.utm_source,
    utm_medium = EXCLUDED.utm_medium,
    utm_term = EXCLUDED.utm_term,
    total_clicks = EXCLUDED.total_clicks,
    last_synced_at = EXCLUDED.last_synced_at
"""


def _normalize_db_url(url: str) -> str:
    """Garante o driver asyncpg e converte ``sslmode`` (libpq) para ``ssl`` (asyncpg)."""
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    url = re.sub(r"([?&])sslmode=", lambda m: m.group(1) + "ssl=", url)
    return url


async def sync_click_totals_to_external_db() -> None:
    settings = get_settings()
    if not settings.external_db_url:
        logger.warning(
            "EXTERNAL_DB_URL não definida: sincronização com o banco externo desativada"
        )
        return

    logger.info("Iniciando sincronização de cliques com o banco externo (tabela %s)",
                settings.external_db_table)

    async with async_session_maker() as db:
        result = await db.execute(
            select(
                Link.short_code,
                Link.title,
                Link.destination_url,
                Link.utm_campaign,
                Link.utm_source,
                Link.utm_medium,
                Link.utm_term,
                Partner.domain,
                func.count(Click.id),
            )
            .outerjoin(Click, Click.link_id == Link.id)
            .outerjoin(Partner, Partner.id == Link.partner_id)
            .group_by(Link.id, Partner.domain)
        )
        totals = result.all()

    try:
        await _push_to_external_db(totals, settings)
    except Exception:
        logger.exception("Falha ao sincronizar cliques com o banco externo")


async def _push_to_external_db(totals, settings) -> None:
    table = settings.external_db_table
    if not _VALID_TABLE_NAME.match(table):
        logger.error("Nome de tabela externa inválido: %r", table)
        return

    engine = create_async_engine(_normalize_db_url(settings.external_db_url), pool_pre_ping=True)
    try:
        synced_at = datetime.now(timezone.utc)
        async with engine.begin() as conn:
            await conn.execute(text(CREATE_TABLE_SQL.format(table=table)))
            for column, definition in (
                ("short_url", "TEXT"),
                ("utm_campaign", "VARCHAR(255)"),
                ("utm_source", "VARCHAR(32)"),
                ("utm_medium", "VARCHAR(255)"),
                ("utm_term", "VARCHAR(32)"),
            ):
                await conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
                )
            for (
                short_code,
                title,
                destination_url,
                utm_campaign,
                utm_source,
                utm_medium,
                utm_term,
                partner_domain,
                total_clicks,
            ) in totals:
                await conn.execute(
                    text(UPSERT_SQL.format(table=table)),
                    {
                        "short_code": short_code,
                        "title": title or "",
                        "destination_url": destination_url or "",
                        "short_url": build_short_url(short_code, partner_domain),
                        "utm_campaign": utm_campaign or "",
                        "utm_source": utm_source or "",
                        "utm_medium": utm_medium or "",
                        "utm_term": utm_term or "",
                        "total_clicks": total_clicks or 0,
                        "last_synced_at": synced_at,
                    },
                )
    finally:
        await engine.dispose()

    logger.info("Sincronizados %d links com o banco externo", len(totals))
