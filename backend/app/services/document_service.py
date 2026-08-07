import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus, DocumentType


async def create_document(
    db: AsyncSession,
    *,
    filename: str,
    storage_path: str,
    file_type: DocumentType,
    file_size_bytes: int,
    uploaded_by: uuid.UUID,
) -> Document:
    document = Document(
        filename=filename,
        storage_path=storage_path,
        file_type=file_type,
        file_size_bytes=file_size_bytes,
        uploaded_by=uploaded_by,
        status=DocumentStatus.UPLOADED,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


async def get_document(db: AsyncSession, document_id: uuid.UUID) -> Document | None:
    result = await db.execute(select(Document).where(Document.id == document_id))
    return result.scalar_one_or_none()


async def list_documents(
    db: AsyncSession, *, offset: int = 0, limit: int = 50
) -> tuple[list[Document], int]:
    count_result = await db.execute(select(func.count()).select_from(Document))
    total = count_result.scalar_one()

    result = await db.execute(
        select(Document).order_by(Document.created_at.desc()).offset(offset).limit(limit)
    )
    items = list(result.scalars().all())
    return items, total


async def update_status(
    db: AsyncSession,
    document: Document,
    status: DocumentStatus,
    message: str | None = None,
    page_count: int | None = None,
    chunk_count: int | None = None,
) -> Document:
    document.status = status
    document.status_message = message
    if page_count is not None:
        document.page_count = page_count
    if chunk_count is not None:
        document.chunk_count = chunk_count
    await db.commit()
    await db.refresh(document)
    return document


async def delete_document(db: AsyncSession, document: Document) -> None:
    await db.delete(document)
    await db.commit()
