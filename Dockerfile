# Multi-stage production Dockerfile for Renewable Asset Intelligence Backend API
FROM python:3.11-slim as base

# Prevent Python from writing pyc files and keep stdout unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install minimal OS runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python package dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .[domain,dev]

# Copy repository source code and assets
COPY rai/ ./rai/
COPY services/ ./services/
COPY data/ ./data/
COPY artifacts/ ./artifacts/

# Create non-root system user for security hardening
RUN useradd -m -u 10001 raiuser && \
    chown -R raiuser:raiuser /app
USER raiuser

# Expose backend API port
EXPOSE 8000

# Docker healthcheck referencing standard liveness probe
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Default execution command
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
