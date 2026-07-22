import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

SHORT_CODE_RE = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")


class LoginRequest(BaseModel):
    username: str
    password: str


class LinkCreate(BaseModel):
    destination_url: str
    title: str | None = None
    custom_code: str | None = None

    @field_validator("destination_url")
    @classmethod
    def validate_destination(cls, value: str) -> str:
        if not re.match(r"^https?://", value, re.IGNORECASE):
            raise ValueError("destination_url deve começar com http:// ou https://")
        return value

    @field_validator("custom_code")
    @classmethod
    def validate_custom_code(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not SHORT_CODE_RE.match(value):
            raise ValueError(
                "custom_code deve ter entre 3 e 64 caracteres alfanuméricos, '-' ou '_'"
            )
        return value


class LinkUpdate(BaseModel):
    destination_url: str | None = None
    title: str | None = None
    is_active: bool | None = None

    @field_validator("destination_url")
    @classmethod
    def validate_destination(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not re.match(r"^https?://", value, re.IGNORECASE):
            raise ValueError("destination_url deve começar com http:// ou https://")
        return value


class LinkOut(BaseModel):
    id: uuid.UUID
    short_code: str
    destination_url: str
    title: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    total_clicks: int = 0
    short_url: str

    class Config:
        from_attributes = True


class DailyClicks(BaseModel):
    date: str
    count: int


class ReferrerCount(BaseModel):
    referrer: str
    count: int


class DeviceCount(BaseModel):
    device_type: str
    count: int


class LinkStats(BaseModel):
    total_clicks: int
    daily_clicks: list[DailyClicks]
    device_breakdown: list[DeviceCount]
    top_referrers: list[ReferrerCount]
