import html
import json
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from app.database import async_session_maker
from app.models import Click, Link
from app.utils.user_agent import detect_device_type

router = APIRouter(tags=["redirect"])

REDIRECT_PAGE_SECONDS = 5

REDIRECT_PAGE_TEMPLATE = """<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="robots" content="noindex" />
  <meta http-equiv="refresh" content="{seconds};url={url_attr}" />
  <title>Redirecionando…</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet" />
  <style>
    :root {{ --bg: #faf9f7; --surface: #fff; --border: #e8e3dd; --text: #2b2d33; --muted: #71757e; --primary: #e2622d; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;
      padding: 16px; background: var(--bg); color: var(--text);
      font-family: "Poppins", "Segoe UI", system-ui, sans-serif;
    }}
    .box {{
      width: 100%; max-width: 440px; text-align: center; background: var(--surface);
      border: 1px solid var(--border); border-radius: 14px; padding: 32px 24px;
      box-shadow: 0 1px 3px rgba(43, 45, 51, .06), 0 6px 16px rgba(226, 98, 45, .05);
    }}
    .lead {{ margin: 0; font-size: 15px; color: var(--muted); }}
    .title {{ margin: 6px 0 24px; font-size: 22px; font-weight: 600; overflow-wrap: anywhere; }}
    .count {{
      width: 88px; height: 88px; margin: 0 auto 20px; border-radius: 50%;
      border: 4px solid var(--primary); display: flex; align-items: center; justify-content: center;
      font-size: 36px; font-weight: 700; color: var(--primary); font-variant-numeric: tabular-nums;
    }}
    a {{ color: var(--primary); font-size: 14px; font-weight: 600; }}
  </style>
</head>
<body>
  <main class="box">
    <p class="lead">Você está sendo redirecionada para:</p>
    <p class="title">{title}</p>
    <div class="count" id="count" aria-live="polite">{seconds}</div>
    <a href="{url_attr}">Ir agora</a>
  </main>
  <script>
    (function () {{
      var url = {url_js};
      var left = {seconds};
      var el = document.getElementById("count");
      var timer = setInterval(function () {{
        left -= 1;
        if (left <= 0) {{
          clearInterval(timer);
          el.textContent = "0";
          window.location.replace(url);
          return;
        }}
        el.textContent = String(left);
      }}, 1000);
    }})();
  </script>
</body>
</html>
"""


def _render_redirect_page(title: str, url: str) -> HTMLResponse:
    page = REDIRECT_PAGE_TEMPLATE.format(
        seconds=REDIRECT_PAGE_SECONDS,
        title=html.escape(title),
        url_attr=html.escape(url, quote=True),
        # json.dumps gera uma string JS válida; "<" escapado impede fechar o <script>
        url_js=json.dumps(url).replace("<", "\\u003c"),
    )
    return HTMLResponse(content=page, headers={"Cache-Control": "no-store"})


def _apply_structured_utm(destination_url: str, link: Link) -> str:
    structured = {
        "utm_campaign": link.utm_campaign,
        "utm_source": link.utm_source,
        "utm_medium": link.utm_medium,
        "utm_term": link.utm_term,
    }
    structured = {key: value for key, value in structured.items() if value}
    if not structured:
        return destination_url

    parts = urlsplit(destination_url)
    query_pairs = [
        (key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key not in structured
    ]
    query_pairs.extend(structured.items())
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_pairs), parts.fragment))


def _apply_click_token(url: str, short_code: str, click_id: uuid.UUID) -> str:
    """Marca o clique em utm_content ('lnk.<código>.<id do clique>') para o funil
    ligar o acesso do site (users_access no Vivart_BI) ao link e ao clique exato.
    Só entra em URLs que já carregam UTM e não têm utm_content próprio."""
    parts = urlsplit(url)
    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    keys = {key for key, _ in query_pairs}
    if "utm_content" in keys or not any(key.startswith("utm_") for key in keys):
        return url
    query_pairs.append(("utm_content", f"lnk.{short_code}.{click_id}"))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_pairs), parts.fragment))


async def _record_click(
    click_id: uuid.UUID, link_id, ip_address: str | None, user_agent: str | None, referrer: str | None
):
    async with async_session_maker() as db:
        click = Click(
            id=click_id,
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

    click_id = uuid.uuid4()
    background_tasks.add_task(
        _record_click,
        click_id,
        link.id,
        client_ip,
        request.headers.get("user-agent"),
        request.headers.get("referer"),
    )

    final_url = _apply_structured_utm(link.destination_url, link)
    final_url = _apply_click_token(final_url, link.short_code, click_id)
    if link.is_redirect_page:
        return _render_redirect_page(link.title or link.short_code, final_url)
    return RedirectResponse(url=final_url, status_code=status.HTTP_302_FOUND)
