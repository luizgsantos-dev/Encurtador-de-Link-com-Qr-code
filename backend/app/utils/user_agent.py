from app.models import DeviceType

BOT_MARKERS = ("bot", "spider", "crawler", "curl", "wget", "python-requests", "facebookexternalhit")
TABLET_MARKERS = ("ipad", "tablet")
MOBILE_MARKERS = ("mobi", "iphone", "ipod", "android")


def detect_device_type(user_agent: str | None) -> DeviceType:
    if not user_agent:
        return DeviceType.unknown

    ua = user_agent.lower()

    if any(marker in ua for marker in BOT_MARKERS):
        return DeviceType.bot
    if any(marker in ua for marker in TABLET_MARKERS):
        return DeviceType.tablet
    if any(marker in ua for marker in MOBILE_MARKERS):
        return DeviceType.mobile
    return DeviceType.desktop
