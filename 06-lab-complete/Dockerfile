# ============================================================
# Production Dockerfile — Travel Chatbot API
# Multi-stage · slim · non-root · healthcheck
# ============================================================

# ── Stage 1: Builder ────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ── Stage 2: Runtime ────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Non-root user (home /home/app để user-site packages resolve đúng)
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy installed packages từ builder (nhỏ hơn, không có build tools)
COPY --from=builder /root/.local /home/app/.local

# Copy application code
COPY app/ ./app/

RUN chown -R app:app /app /home/app

USER app

ENV PATH=/home/app/.local/bin:$PATH \
    PYTHONUSERBASE=/home/app/.local \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Healthcheck — dùng PORT nếu được inject (Railway), mặc định 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://localhost:%s/health' % os.getenv('PORT','8000'))" || exit 1

# Shell form để $PORT được expand (Railway inject PORT runtime)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
