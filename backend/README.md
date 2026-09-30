# EnterpriseGPT — Backend (Phase 1)

Foundation + Document Intelligence Pipeline for the EnterpriseGPT secure
enterprise RAG assistant.

## What Phase 1 delivers

- FastAPI backend with async SQLAlchemy + PostgreSQL + Alembic
- JWT auth (register/login) with `admin` / `employee` roles — first
  registered user automatically becomes admin
- Document upload (PDF, DOCX, TXT, CSV) with validation and disk storage
- Full ingestion pipeline: **extract → clean → chunk → embed → store**
  - Extraction: PyMuPDF (PDF), python-docx (DOCX), native readers (TXT/CSV)
  - Chunking: `RecursiveCharacterTextSplitter`, page numbers preserved for PDFs
  - Embeddings: Sentence Transformers (`all-MiniLM-L6-v2`, 384-dim)
  - Vector storage: Qdrant, one point per chunk, payload includes
    `document_id`, `chunk_id`, `page_number`, `filename`, `text`
- Pipeline runs as a FastAPI `BackgroundTask` so upload requests return
  immediately; document status (`uploaded → processing → ready|failed`)
  is polled via `GET /api/v1/documents/{id}`

## Folder structure

```
backend/
  app/
    api/            # auth, documents, health routers + shared deps
    core/            # config, security (JWT/bcrypt), logging
    database/        # async engine/session, declarative base
    models/          # SQLAlchemy ORM: User, Document, DocumentChunk
    schemas/         # Pydantic request/response models
    services/        # storage, validation, extraction, chunking,
                      # embedding, vector store, pipeline orchestration
    main.py
  alembic/            # migrations (initial schema in versions/0001_*.py)
  requirements.txt
  Dockerfile
  docker-compose.yml  # postgres + qdrant + backend
  .env.example
```

## Why this structure

- **Postgres is the source of truth**, Qdrant is a rebuildable search
  index. Chunk text + metadata live in `document_chunks`; the chunk
  row's UUID is reused as the Qdrant point ID, so the two stores are
  always consistent and the vector index can be rebuilt from Postgres
  if it's ever lost.
- **Services are framework-agnostic.** Extraction, chunking, embedding,
  and vector storage are plain Python modules with no FastAPI
  dependency — they're independently testable and reusable from the
  Phase 2 RAG pipeline without modification.
- **Pipeline runs out-of-request.** Embedding generation and vector
  upserts are too slow to hold an HTTP request open; the background
  task pattern here is a natural place to swap in a real task queue
  (Celery/RQ) in Phase 5 without changing the pipeline logic itself.

## Setup

```bash
cp .env.example .env
# edit .env — at minimum set a real SECRET_KEY

docker compose up --build
```

This starts Postgres, Qdrant, and the API on `http://localhost:8000`
(interactive docs at `/docs`).

Run migrations (first time, or after pulling new migrations):

```bash
docker compose exec backend alembic upgrade head
```

### Running without Docker

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# start your own Postgres + Qdrant, point .env at them
alembic upgrade head
uvicorn app.main:app --reload
```

## API surface (Phase 1)

| Method | Path                       | Auth        | Purpose                          |
|--------|----------------------------|-------------|-----------------------------------|
| POST   | `/api/v1/auth/register`    | none        | Create account                    |
| POST   | `/api/v1/auth/login`       | none        | Get JWT (OAuth2 password form)    |
| GET    | `/api/v1/auth/me`          | any user    | Current user profile              |
| POST   | `/api/v1/documents/upload` | admin       | Upload + queue for processing     |
| GET    | `/api/v1/documents`        | any user    | List documents (paginated)        |
| GET    | `/api/v1/documents/{id}`   | any user    | Get one document + status         |
| DELETE | `/api/v1/documents/{id}`   | admin       | Delete document + its vectors     |

## Known Phase 1 limitations (by design — addressed in later phases)

- No RAG/Q&A endpoint yet — that's Phase 2.
- Upload is admin-only; per-document/per-role ACLs land in Phase 4.
- No refresh tokens / rate limiting yet — hardened in Phase 5.
- Embedding model runs synchronously in the background task (fine for a
  demo; Phase 5 discusses moving to a proper worker queue for scale).
