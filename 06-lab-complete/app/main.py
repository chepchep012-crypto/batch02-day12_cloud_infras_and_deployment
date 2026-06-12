"""
Production Travel Chatbot API — Day 12 deployment lab.

Lấy chatbot du lịch từ Day 5-6 Hackathon và "production-hoá":
  ✅ 12-factor config từ environment
  ✅ Structured JSON logging
  ✅ Health (liveness) + Readiness probe
  ✅ CORS + security headers
  ✅ Request observability middleware
  ✅ Graceful shutdown (SIGTERM)
"""
import json
import logging
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat

# ─────────────────────────────────────────────────────────
# Logging — JSON structured
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger("travel-chatbot")

START_TIME = time.time()
_is_ready = False
_request_count = 0


# ─────────────────────────────────────────────────────────
# Lifespan — startup / shutdown
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "llm": settings.llm_mode,
    }))
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))


# ─────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observability(request: Request, call_next):
    global _request_count
    _request_count += 1
    start = time.time()
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    logger.info(json.dumps({
        "event": "request",
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "ms": round((time.time() - start) * 1000, 1),
    }))
    return response


app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


# ─────────────────────────────────────────────────────────
# Info + Ops endpoints
# ─────────────────────────────────────────────────────────
@app.get("/", tags=["info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs",
        "health": "/health",
        "chat": "POST /api/chat/",
    }


@app.get("/health", tags=["ops"])
def health():
    """Liveness probe — platform restart container nếu fail."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "llm": settings.llm_mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["ops"])
def ready():
    """Readiness probe — load balancer ngừng route nếu chưa sẵn sàng."""
    if not _is_ready:
        return Response(
            content=json.dumps({"ready": False}),
            status_code=503,
            media_type="application/json",
        )
    return {"ready": True}


# ─────────────────────────────────────────────────────────
# Graceful shutdown
# ─────────────────────────────────────────────────────────
def _handle_sigterm(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))


signal.signal(signal.SIGTERM, _handle_sigterm)
