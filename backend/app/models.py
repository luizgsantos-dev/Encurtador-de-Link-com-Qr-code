import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Table, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeviceType(str, enum.Enum):
    mobile = "mobile"
    desktop = "desktop"
    tablet = "tablet"
    bot = "bot"
    unknown = "unknown"


user_groups = Table(
    "user_groups",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    groups: Mapped[list["Group"]] = relationship(secondary=user_groups, back_populates="users")


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(secondary=user_groups, back_populates="groups")


class Link(Base):
    __tablename__ = "links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    short_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    destination_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    group: Mapped["Group | None"] = relationship()
    clicks: Mapped[list["Click"]] = relationship(
        back_populates="link", cascade="all, delete-orphan"
    )


class Click(Base):
    __tablename__ = "clicks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    link_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("links.id", ondelete="CASCADE"), nullable=False
    )
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    referrer: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_type: Mapped[DeviceType] = mapped_column(
        String(16), default=DeviceType.unknown, nullable=False
    )

    link: Mapped["Link"] = relationship(back_populates="clicks")

    __table_args__ = (Index("ix_clicks_link_id_clicked_at", "link_id", "clicked_at"),)
