from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.database import async_session_maker
from app.models import Click, Link
from app.utils.user_agent import detect_device_type

router = APIRouter(tags=["redirect"])


async def _record_click(link_id, ip_address: str | None, user_agent: str | None, referrer: str | None):
    async with async_session_maker() as db:
        click = Click(
            link_id=link_id,
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer,
            device_type=detect_device_type(user_agent),
        )
        db.add(click)
        await db.commit()


@router.get("/{short_code}")
async def redirect_to_destination(
    short_code: str, request: Request, background_tasks: BackgroundTasks
):
    async with async_session_maker() as db:
        link = await db.scalar(
            select(Link).where(Link.short_code == short_code, Link.is_active.is_(True))
        )

    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link não encontrado")

    forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (
        request.client.host if request.client else None
    )

    background_tasks.add_task(
        _record_click,
        link.id,
        client_ip,
        request.headers.get("user-agent"),
        request.headers.get("referer"),
    )

    return RedirectResponse(url=link.destination_url, status_code=status.HTTP_302_FOUND)
