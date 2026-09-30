import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.models.chunk import DocumentChunk
from app.models.document import DocumentStatus
from app.services import document_service
from app.services.chunking_service import chunk_extraction_result
from app.services.embedding_service import embedding_service
from app.services.extraction_service import ExtractionError, extract_text
from app.services.vector_store_service import vector_store_service

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    pass


async def process_document(document_id: uuid.UUID) -> None:
    """
    Full ingestion pipeline for a single document:

        Extract text -> Clean -> Split into chunks -> Generate embeddings
        -> Store chunk rows in Postgres -> Store vectors in Qdrant

    Runs as a FastAPI BackgroundTask, so it owns its own DB session rather
    than reusing the request-scoped one (which closes when the response
    returns).
    """
    async with AsyncSessionLocal() as db:
        document = await document_service.get_document(db, document_id)
        if document is None:
            logger.error("process_document: document %s not found", document_id)
            return

        try:
            await document_service.update_status(db, document, DocumentStatus.PROCESSING)

            # 1. Extract
            extraction = extract_text(document.storage_path, document.file_type)
            if not extraction.full_text.strip():
                raise PipelineError("No extractable text found in document.")

            # 2 & 3. Clean + chunk (cleaning happens inside chunk_extraction_result)
            chunks = chunk_extraction_result(extraction)
            if not chunks:
                raise PipelineError("Document produced no chunks after splitting.")

            # 4. Generate embeddings
            vectors = embedding_service.embed_texts([c.content for c in chunks])

            # 5. Persist chunk rows in Postgres
            chunk_rows: list[DocumentChunk] = []
            for chunk in chunks:
                row = DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    page_number=chunk.page_number,
                    token_count=_approx_token_count(chunk.content),
                    embedding_status="embedded",
                )
                db.add(row)
                chunk_rows.append(row)
            await db.commit()
            for row in chunk_rows:
                await db.refresh(row)

            # 6. Store vectors in Qdrant, keyed by the Postgres chunk row id
            payloads = [
                {
                    "document_id": str(document.id),
                    "chunk_id": str(row.id),
                    "chunk_index": row.chunk_index,
                    "page_number": row.page_number,
                    "filename": document.filename,
                    "text": row.content,
                }
                for row in chunk_rows
            ]
            vector_store_service.upsert_chunks(
                chunk_ids=[row.id for row in chunk_rows],
                vectors=vectors,
                payloads=payloads,
            )

            await document_service.update_status(
                db,
                document,
                DocumentStatus.READY,
                message=None,
                page_count=extraction.page_count,
                chunk_count=len(chunk_rows),
            )
            logger.info(
                "Document %s processed successfully (%d chunks)", document.id, len(chunk_rows)
            )

        except ExtractionError as exc:
            logger.warning("Extraction failed for document %s: %s", document.id, exc)
            await document_service.update_status(
                db, document, DocumentStatus.FAILED, message=str(exc)
            )
        except PipelineError as exc:
            logger.warning("Pipeline failed for document %s: %s", document.id, exc)
            await document_service.update_status(
                db, document, DocumentStatus.FAILED, message=str(exc)
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected pipeline failure for document %s", document.id)
            await document_service.update_status(
                db, document, DocumentStatus.FAILED, message=f"Unexpected error: {exc}"
            )


def _approx_token_count(text: str) -> int:
    # Rough heuristic (~4 chars/token for English) — good enough for
    # analytics/display; not used for model context-window accounting.
    return max(1, len(text) // 4)
