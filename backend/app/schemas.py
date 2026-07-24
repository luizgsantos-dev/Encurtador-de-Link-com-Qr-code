import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

SHORT_CODE_RE = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")
DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
UTM_SOURCE_VALUES = {"influencer", "marca_parceira"}
UTM_TERM_VALUES = {"ig", "facebook", "youtube", "tiktok", "qrcode"}


def _normalize_utm_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class LoginRequest(BaseModel):
    username: str
    password: str


class LinkCreate(BaseModel):
    destination_url: str
    title: str
    custom_code: str | None = None
    group_id: uuid.UUID
    partner_id: uuid.UUID | None = None
    utm_campaign: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_term: str | None = None

    @field_validator("destination_url")
    @classmethod
    def validate_destination(cls, value: str) -> str:
        if not re.match(r"^https?://", value, re.IGNORECASE):
            raise ValueError("destination_url deve começar com http:// ou https://")
        return value

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title não pode ser vazio")
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

    @field_validator("utm_campaign", "utm_medium")
    @classmethod
    def validate_utm_text(cls, value: str | None) -> str | None:
        return _normalize_utm_text(value)

    @field_validator("utm_source")
    @classmethod
    def validate_utm_source(cls, value: str | None) -> str | None:
        value = _normalize_utm_text(value)
        if value is not None and value not in UTM_SOURCE_VALUES:
            raise ValueError("utm_source deve ser 'influencer' ou 'marca_parceira'")
        return value

    @field_validator("utm_term")
    @classmethod
    def validate_utm_term(cls, value: str | None) -> str | None:
        value = _normalize_utm_text(value)
        if value is not None and value not in UTM_TERM_VALUES:
            raise ValueError("utm_term deve ser um dos valores: ig, facebook, youtube, tiktok, qrcode")
        return value

    @model_validator(mode="after")
    def validate_utm_requires_partner(self) -> "LinkCreate":
        has_utm = any([self.utm_campaign, self.utm_source, self.utm_medium, self.utm_term])
        if has_utm and not self.partner_id:
            raise ValueError("utm_campaign, utm_source, utm_medium e utm_term só podem ser definidos em links vinculados a um parceiro")
        return self


class LinkUpdate(BaseModel):
    destination_url: str | None = None
    title: str | None = None
    is_active: bool | None = None
    group_id: uuid.UUID | None = None
    partner_id: uuid.UUID | None = None
    clear_partner: bool = False
    utm_campaign: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_term: str | None = None

    @field_validator("destination_url")
    @classmethod
    def validate_destination(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not re.match(r"^https?://", value, re.IGNORECASE):
            raise ValueError("destination_url deve começar com http:// ou https://")
        return value

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("title não pode ser vazio")
        return value

    @field_validator("utm_campaign", "utm_medium")
    @classmethod
    def validate_utm_text(cls, value: str | None) -> str | None:
        return _normalize_utm_text(value)

    @field_validator("utm_source")
    @classmethod
    def validate_utm_source(cls, value: str | None) -> str | None:
        value = _normalize_utm_text(value)
        if value is not None and value not in UTM_SOURCE_VALUES:
            raise ValueError("utm_source deve ser 'influencer' ou 'marca_parceira'")
        return value

    @field_validator("utm_term")
    @classmethod
    def validate_utm_term(cls, value: str | None) -> str | None:
        value = _normalize_utm_text(value)
        if value is not None and value not in UTM_TERM_VALUES:
            raise ValueError("utm_term deve ser um dos valores: ig, facebook, youtube, tiktok, qrcode")
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
    group_id: uuid.UUID | None
    group_name: str | None
    partner_id: uuid.UUID | None
    partner_name: str | None
    utm_campaign: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_term: str | None

    class Config:
        from_attributes = True


class GroupOut(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class GroupCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name não pode ser vazio")
        return value


class GroupUpdate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name não pode ser vazio")
        return value


def _validate_domain(value: str | None) -> str | None:
    if value is None or value.strip() == "":
        return None
    value = value.strip().lower()
    if re.match(r"^https?://", value) or "/" in value or " " in value:
        raise ValueError("domain deve ser apenas o host, sem protocolo ou caminho (ex: joao.encurtador.com.br)")
    if not DOMAIN_RE.match(value):
        raise ValueError("domain inválido")
    return value


class PartnerCreate(BaseModel):
    name: str
    social_media: str | None = None
    email: str | None = None
    phone: str | None = None
    description: str | None = None
    partnership: str | None = None
    domain: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name não pode ser vazio")
        return value

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str | None) -> str | None:
        return _validate_domain(value)


class PartnerUpdate(BaseModel):
    name: str | None = None
    social_media: str | None = None
    email: str | None = None
    phone: str | None = None
    description: str | None = None
    partnership: str | None = None
    domain: str | None = None
    clear_domain: bool = False
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("name não pode ser vazio")
        return value

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str | None) -> str | None:
        return _validate_domain(value)


class PartnerOut(BaseModel):
    id: uuid.UUID
    name: str
    social_media: str | None
    email: str | None
    phone: str | None
    description: str | None
    partnership: str | None
    domain: str | None
    is_active: bool
    created_at: datetime
    total_links: int = 0
    total_clicks: int = 0

    class Config:
        from_attributes = True


class UserGroupOut(BaseModel):
    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    password: str
    is_admin: bool = False
    group_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("username deve ter ao menos 3 caracteres")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 6:
            raise ValueError("password deve ter ao menos 6 caracteres")
        return value


class UserUpdate(BaseModel):
    password: str | None = None
    is_admin: bool | None = None
    is_active: bool | None = None
    group_ids: list[uuid.UUID] | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if len(value) < 6:
            raise ValueError("password deve ter ao menos 6 caracteres")
        return value


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    is_admin: bool
    is_active: bool
    created_at: datetime
    groups: list[UserGroupOut]

    class Config:
        from_attributes = True


class MeOut(BaseModel):
    id: uuid.UUID
    username: str
    is_admin: bool
    groups: list[UserGroupOut]

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


class PartnerLinkStat(BaseModel):
    id: uuid.UUID
    title: str | None
    short_code: str
    short_url: str
    total_clicks: int


class PartnerStats(BaseModel):
    total_clicks: int
    daily_clicks: list[DailyClicks]
    links: list[PartnerLinkStat]


class TopLinkStat(BaseModel):
    id: uuid.UUID
    title: str | None
    total_clicks: int


class DashboardOverview(BaseModel):
    daily_clicks_total: list[DailyClicks]
    daily_clicks_partner: list[DailyClicks]
    daily_clicks_general: list[DailyClicks]
    top_links: list[TopLinkStat]
