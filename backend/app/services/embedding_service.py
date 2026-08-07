import logging
import threading

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    """
    Thin wrapper around Sentence Transformers.

    The model is loaded lazily and cached as a singleton — loading it is
    relatively expensive (disk + memory), and we don't want every request
    to pay that cost. Thread-safe via a simple lock since FastAPI can run
    sync code in a threadpool.
    """

    _model: SentenceTransformer | None = None
    _lock = threading.Lock()

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    logger.info("Loading embedding model: %s", settings.embedding_model)
                    self._model = SentenceTransformer(settings.embedding_model)
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        vectors = model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


embedding_service = EmbeddingService()
