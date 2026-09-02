# ===================================================
# Stage 1: Build React Frontend
# ===================================================
FROM node:22-alpine AS frontend-builder

WORKDIR /build/frontend

# Copy frontend package manifests
COPY frontend/package*.json ./
RUN npm install

# Copy frontend source code and build
COPY frontend/ ./
RUN npm run build

# ===================================================
# Stage 2: Python Backend Runtime
# ===================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies for OpenCV and multimedia
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code, models, and configs
COPY src/ ./src/
COPY static/ ./static/
COPY server.py ai_engine.py custom_tracker.yaml ./
COPY *.pt ./

# Copy built React frontend from Stage 1
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

# Create uploads and models directory
RUN mkdir -p uploads models

# Expose FastAPI & WebSocket port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/api/models || exit 1

# Start Server
CMD ["python", "server.py"]
