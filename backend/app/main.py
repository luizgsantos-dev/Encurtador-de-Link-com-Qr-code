from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import func, select, text

from app.config import get_settings
from app.database import Base, async_session_maker, engine
from app.models import User
from app.routers import auth, groups, links, partners, redirect, stats, users
from app.security import hash_password

settings = get_settings()


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

    yield


app = FastAPI(title="Encurtador de Links", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(partners.router)
app.include_router(links.router)
app.include_router(stats.router)
app.include_router(stats.overview_router)
app.include_router(redirect.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
