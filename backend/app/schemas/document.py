import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus, DocumentType
from app.models.user import Department


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    file_type: DocumentType
    file_size_bytes: int
    status: DocumentStatus
    status_message: str | None
    page_count: int | None
    chunk_count: int | None
    allowed_departments: list[Department] = Field(default_factory=list)
    uploaded_by: uuid.UUID
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    document: DocumentRead


class DocumentListResponse(BaseModel):
    total: int
    items: list[DocumentRead]


class DocumentACLUpdate(BaseModel):
    """Admin-only: set which departments can see this document. Empty = everyone."""
    allowed_departments: list[Department] = Field(default_factory=list)


class DocumentPermissionCreate(BaseModel):
    user_id: uuid.UUID


class DocumentPermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime