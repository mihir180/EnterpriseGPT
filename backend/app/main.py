import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, auth, documents, evaluation, health
from app.api.chat import router as chat_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
setup_logging(level=logging.INFO)
settings = get_settings()

app = FastAPI(
    title="EnterpriseGPT API",
    description="Secure Enterprise RAG AI Assistant — document intelligence & Q&A backend.",
    version="0.1.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat_router)
app.include_router(analytics.router)
app.include_router(evaluation.router)


@app.get("/")
async def root() -> dict:
    return {"service": "EnterpriseGPT API", "status": "running", "docs": "/docs"}
