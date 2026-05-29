# Multi-stage build for production
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*


# Builder stage
FROM base as builder

COPY requirements.txt .

RUN pip install --user --no-warn-script-location -r requirements.txt


# Final stage
FROM base

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Set PATH to include user pip installations
ENV PATH=/root/.local/bin:$PATH

COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs /app/data /app/vectorstore && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run with gunicorn for production
CMD ["gunicorn", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--access-logfile", "logs/access.log", \
     "--error-logfile", "logs/error.log", \
     "--log-level", "info", \
     "app.main:app"]