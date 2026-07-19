# ============================================================
# Stage 1: Builder
# ============================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files for layer caching
COPY pyproject.toml ./
RUN pip install --user --no-cache-dir .

# Copy source for wheel build
COPY app/ ./app/
RUN pip wheel --no-deps --wheel-dir /wheels .

# ============================================================
# Stage 2: Runtime
# ============================================================
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    cron \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appgroup && useradd -r -g appgroup -m -d /app appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /usr/local

# Copy application code
COPY app/ ./app/
COPY frontend/ ./frontend/
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN mkdir -p /app/data /var/log/supervisor \
    && chown appuser:appgroup /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
