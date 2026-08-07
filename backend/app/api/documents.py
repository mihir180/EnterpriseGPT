import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_admin, get_current_user, require_admin
from app.database.session import get_db
from app.models.document import Document
from app.models.document_permission import DocumentPermission
from app.models.user import User
from app.schemas.document import (
    DocumentACLUpdate,
    DocumentListResponse,
    DocumentPermissionCreate,
    DocumentPermissionRead,
    DocumentRead,
    DocumentUploadResponse,
)
from app.services import document_service
from app.services.pipeline_service import process_document
from app.services.storage_service import storage_service
from app.services.validation_service import validate_size, validate_upload
from app.services.vector_store_service import vector_store_service

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> DocumentUploadResponse:
    """
    Upload a document for ingestion. Restricted to admins in Phase 1 —
    Phase 4 introduces per-document ACLs for finer-grained control.
    """
    file_type = validate_upload(file)
    storage_path, size_bytes = await storage_service.save_upload(file)
    validate_size(size_bytes)

    document = await document_service.create_document(
        db,
        filename=file.filename,
        storage_path=storage_path,
        file_type=file_type,
        file_size_bytes=size_bytes,
        uploaded_by=current_user.id,
    )

    # Processing happens asynchronously so the upload request returns fast;
    # the client polls GET /documents/{id} (or a future websocket) for status.
    background_tasks.add_task(process_document, document.id)

    return DocumentUploadResponse(document=DocumentRead.model_validate(document))


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    items, total = await document_service.list_documents(db, offset=offset, limit=limit)
    return DocumentListResponse(
        total=total, items=[DocumentRead.model_validate(d) for d in items]
    )


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    document = await document_service.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return DocumentRead.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
) -> None:
    document = await document_service.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    vector_store_service.delete_by_document(document.id)
    storage_service.delete_file(document.storage_path)
    await document_service.delete_document(db, document)


async def _get_document_or_404(db: AsyncSession, document_id: uuid.UUID) -> Document:
    doc = await db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return doc


@router.patch("/{document_id}/acl", response_model=DocumentRead)
async def update_document_acl(
    document_id: uuid.UUID,
    payload: DocumentACLUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Document:
    """Set which departments can see this document. Empty list = visible org-wide."""
    doc = await _get_document_or_404(db, document_id)
    doc.allowed_departments = [d.value for d in payload.allowed_departments]
    await db.commit()
    await db.refresh(doc)
    return doc


@router.post(
    "/{document_id}/permissions",
    response_model=DocumentPermissionRead,
    status_code=status.HTTP_201_CREATED,
)
async def grant_document_permission(
    document_id: uuid.UUID,
    payload: DocumentPermissionCreate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> DocumentPermission:
    """Explicitly grant one user access to this document, regardless of department."""
    await _get_document_or_404(db, document_id)

    existing = await db.execute(
        select(DocumentPermission).where(
            DocumentPermission.document_id == document_id,
            DocumentPermission.user_id == payload.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Permission already granted."
        )

    grant = DocumentPermission(document_id=document_id, user_id=payload.user_id)
    db.add(grant)
    await db.commit()
    await db.refresh(grant)
    return grant


@router.delete(
    "/{document_id}/permissions/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def revoke_document_permission(
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(DocumentPermission).where(
            DocumentPermission.document_id == document_id,
            DocumentPermission.user_id == user_id,
        )
    )
    grant = result.scalar_one_or_none()
    if grant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found.")
    await db.delete(grant)
    await db.commit()