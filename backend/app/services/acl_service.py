"""
Document access control.

Every retrieval path (chat, search, document listing) must funnel through
`get_accessible_document_ids` before hitting Qdrant or Postgres for chunk
content. This is the single choke point for Phase 4 ACL — deliberately kept
in one small module so there's exactly one place to audit.

Rule set:
  - Admins: unrestricted (returns None, meaning "no filter").
  - A document with an empty `allowed_departments` list is public — every
    authenticated user can see it.
  - A document with a non-empty `allowed_departments` list is visible to:
      * users whose own `department` is in that list, OR
      * users with an explicit DocumentPermission grant for that document.
"""
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_permission import DocumentPermission
from app.models.user import User, UserRole


async def get_accessible_document_ids(
    db: AsyncSession, user: User
) -> list[uuid.UUID] | None:
    """Returns None for "no restriction" (admin), else an explicit allow-list."""
    if user.role == UserRole.ADMIN:
        return None

    granted_subq = (
        select(DocumentPermission.document_id)
        .where(DocumentPermission.user_id == user.id)
    )

    stmt = select(Document.id).where(
        or_(
            func.jsonb_array_length(Document.allowed_departments) == 0,
            Document.allowed_departments.contains([user.department.value]),
            Document.id.in_(granted_subq),
        )
    )
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


async def can_access_document(
    db: AsyncSession, user: User, document: Document
) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    if not document.allowed_departments:
        return True
    if user.department.value in document.allowed_departments:
        return True

    result = await db.execute(
        select(DocumentPermission).where(
            DocumentPermission.document_id == document.id,
            DocumentPermission.user_id == user.id,
        )
    )
    return result.scalar_one_or_none() is not None


async def get_department_document_ids(
    db: AsyncSession, department: str
) -> list[uuid.UUID]:
    """Documents relevant to a department topic for agent routing: either
    explicitly tagged for that department, OR public (untagged) documents,
    which should remain searchable regardless of the classified topic."""
    result = await db.execute(
        select(Document.id).where(
            or_(
                Document.allowed_departments.contains([department]),
                func.jsonb_array_length(Document.allowed_departments) == 0,
            )
        )
    )
    return [row[0] for row in result.all()]
