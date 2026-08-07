"""
Refresh token lifecycle. Raw tokens are opaque random strings (not JWTs --
no need to encode claims in them, they're just a lookup key), hashed with
SHA-256 before storage so the DB never holds a usable raw token.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.refresh_token import RefreshToken

settings = get_settings()


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def issue_refresh_token(db: AsyncSession, user_id: uuid.UUID) -> str:
    raw_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

    record = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw_token),
        expires_at=expires_at,
    )
    db.add(record)
    await db.commit()
    return raw_token


async def rotate_refresh_token(
    db: AsyncSession, raw_token: str
) -> tuple[str, uuid.UUID] | None:
    token_hash = _hash_token(raw_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()

    if record is None:
        return None
    if record.revoked:
        return None
    if record.expires_at < datetime.now(timezone.utc):
        return None

    new_raw_token = secrets.token_urlsafe(48)
    new_record = RefreshToken(
        user_id=record.user_id,
        token_hash=_hash_token(new_raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(new_record)
    await db.flush()

    record.revoked = True
    record.replaced_by_id = new_record.id
    await db.commit()

    return new_raw_token, record.user_id


async def revoke_all_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked == False  # noqa: E712
        )
    )
    for record in result.scalars().all():
        record.revoked = True
    await db.commit()
