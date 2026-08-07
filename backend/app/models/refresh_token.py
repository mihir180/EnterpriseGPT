"""
Refresh tokens, stored server-side so they can be revoked (e.g. on logout,
password change, or admin-forced deactivation) — unlike the short-lived
access token, which is a stateless JWT that can't be individually revoked
before it expires.

Flow:
  - Login issues both an access token (short-lived, ~15-60 min) and a
    refresh token (long-lived, ~7-30 days, stored here hashed).
  - POST /api/v1/auth/refresh exchanges a valid refresh token for a new
    access token AND rotates the refresh token (old one is revoked, a new
    one issued) — rotation limits the damage window if a refresh token
    ever leaks.
  - Logout / "revoke all sessions" simply marks rows as revoked here.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class RefreshToken(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("refresh_tokens.id"), nullable=True
    )

    user = relationship("User")

    def __repr__(self) -> str:
        return f"<RefreshToken user={self.user_id} revoked={self.revoked}>"
