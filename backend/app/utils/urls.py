from app.config import get_settings

settings = get_settings()


def build_short_url(short_code: str, domain: str | None = None) -> str:
    if domain:
        return f"https://{domain}/{short_code}"
    return f"{settings.base_url}/{short_code}"
