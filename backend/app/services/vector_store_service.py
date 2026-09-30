import logging
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VectorStoreService:
    def __init__(self) -> None:
        self._client: QdrantClient | None = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key or None,
            )
        return self._client

    def ensure_collection(self) -> None:
        collections = {c.name for c in self.client.get_collections().collections}
        if settings.qdrant_collection in collections:
            return

        logger.info("Creating Qdrant collection: %s", settings.qdrant_collection)
        self.client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=qmodels.VectorParams(
                size=settings.embedding_dim,
                distance=qmodels.Distance.COSINE,
            ),
        )
        # Payload indexes speed up filtering by document_id / role during search.
        self.client.create_payload_index(
            collection_name=settings.qdrant_collection,
            field_name="document_id",
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
        )

    def upsert_chunks(
        self,
        chunk_ids: list[uuid.UUID],
        vectors: list[list[float]],
        payloads: list[dict],
    ) -> None:
        if not (len(chunk_ids) == len(vectors) == len(payloads)):
            raise ValueError("chunk_ids, vectors, and payloads must be the same length")

        self.ensure_collection()

        points = [
            qmodels.PointStruct(id=str(chunk_id), vector=vector, payload=payload)
            for chunk_id, vector, payload in zip(chunk_ids, vectors, payloads)
        ]
        self.client.upsert(collection_name=settings.qdrant_collection, points=points)

    def delete_by_document(self, document_id: uuid.UUID) -> None:
        self.client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=str(document_id)),
                        )
                    ]
                )
            ),
        )

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        document_ids: list[uuid.UUID] | None = None,
    ) -> list[qmodels.ScoredPoint]:
        query_filter = None
        if document_ids is not None:
            query_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchAny(any=[str(d) for d in document_ids]),
                    )
                ]
            )

        return self.client.search(
            collection_name=settings.qdrant_collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter,
        )


vector_store_service = VectorStoreService()
