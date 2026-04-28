# =============================================================================
#  Stage 1 — Build the Svelte frontend
# =============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# =============================================================================
#  Stage 2 — Runtime image (Python + frontend assets)
# =============================================================================
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata + source
COPY pyproject.toml ./
COPY src/ src/

# Install routie with all extras (web + db)
RUN pip install --no-cache-dir -e ".[web,db,graphhopper]"

# Copy the built frontend assets
COPY --from=frontend-builder /build/frontend/dist frontend/dist/

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8000/api/v1/health | grep -q '"ok"' || exit 1

EXPOSE 8000

CMD ["uvicorn", "routie.main:app", "--host", "0.0.0.0", "--port", "8000"]
