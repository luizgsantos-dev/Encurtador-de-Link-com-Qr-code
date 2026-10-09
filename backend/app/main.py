import logging
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from sqlalchemy import func, select, text

from app.postgres_sync import sync_click_totals_to_external_db
from app.config import get_settings
from app.database import Base, async_session_maker, engine
from app.models import User
from app.routers import auth, funnel, groups, links, partners, redirect, stats, users
from app.security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # migração leve para bancos criados antes da introdução de grupos
        await conn.execute(text("ALTER TABLE links ADD COLUMN IF NOT EXISTS group_id UUID"))
        await conn.execute(text("ALTER TABLE links DROP CONSTRAINT IF EXISTS links_group_id_fkey"))
        await conn.execute(
            text(
                "ALTER TABLE links ADD CONSTRAINT links_group_id_fkey "
                "FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE SET NULL"
            )
        )
        # migração leve para bancos criados antes da introdução de parceiros
        await conn.execute(text("ALTER TABLE links ADD COLUMN IF NOT EXISTS partner_id UUID"))
        await conn.execute(text("ALTER TABLE links DROP CONSTRAINT IF EXISTS links_partner_id_fkey"))
        await conn.execute(
            text(
                "ALTER TABLE links ADD CONSTRAINT links_partner_id_fkey "
                "FOREIGN KEY (partner_id) REFERENCES partners(id) ON DELETE SET NULL"
            )
        )
        # migração leve para bancos criados antes do domínio próprio de parceiro
        await conn.execute(text("ALTER TABLE partners ADD COLUMN IF NOT EXISTS domain VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE partners DROP CONSTRAINT IF EXISTS partners_domain_key"))
        await conn.execute(
            text("ALTER TABLE partners ADD CONSTRAINT partners_domain_key UNIQUE (domain)")
        )
        # migração leve para bancos criados antes do UTM estruturado por parceiro
        await conn.execute(text("ALTER TABLE links ADD COLUMN IF NOT EXISTS utm_campaign VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE links ADD COLUMN IF NOT EXISTS utm_source VARCHAR(32)"))
        await conn.execute(text("ALTER TABLE links ADD COLUMN IF NOT EXISTS utm_medium VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE links ADD COLUMN IF NOT EXISTS utm_term VARCHAR(32)"))
        # migração leve para bancos criados antes do link de redirecionamento
        await conn.execute(
            text("ALTER TABLE links ADD COLUMN IF NOT EXISTS is_redirect_page BOOLEAN NOT NULL DEFAULT false")
        )

    async with async_session_maker() as db:
        user_count = await db.scalar(select(func.count(User.id)))
        if user_count == 0:
            db.add(
                User(
                    username=settings.admin_username,
                    password_hash=hash_password(settings.admin_password),
                    is_admin=True,
                    is_active=True,
                )
            )
            await db.commit()

    scheduler.add_job(
        sync_click_totals_to_external_db,
        trigger=IntervalTrigger(hours=24),
        next_run_time=datetime.now(),
        id="external_db_click_sync",
        replace_existing=True,
    )
    scheduler.start()

    yield

    scheduler.shutdown()


app = FastAPI(title="Encurtador de Links", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(partners.router)
app.include_router(links.router)
app.include_router(stats.router)
app.include_router(stats.overview_router)
app.include_router(funnel.router)
app.include_router(redirect.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
