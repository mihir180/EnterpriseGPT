"""
Application-level rate limiting, using slowapi (a FastAPI-friendly wrapper
around limits/Flask-Limiter's algorithm), backed by Redis so limits are
shared correctly across multiple gunicorn workers (an in-memory limiter
would give each worker its own separate counter, which quietly triples
your real limit with 3 workers).

This sits *behind* nginx's connection-level rate limiting (see
nginx/nginx.conf) — nginx stops raw floods, this stops abuse of specific
expensive endpoints (LLM calls, uploads) with per-route limits.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    default_limits=["200/minute"],  # generous global default; tighten per-route
)


async def rate_limit_exceeded_handler(request: Request, exc) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please slow down and try again shortly."
        },
    )


# Suggested per-route limits (apply where noted above):
#   POST /api/v1/chat/ask          -> "20/minute"   (LLM calls are expensive)
#   POST /api/v1/documents/upload  -> "10/minute"   (embedding is expensive)
#   POST /api/v1/auth/login        -> "10/minute"   (brute-force protection)
#   POST /api/v1/auth/register     -> "5/minute"    (signup abuse protection)
#   POST /api/v1/evaluation/run    -> "5/minute"    (runs the full pipeline N times)
