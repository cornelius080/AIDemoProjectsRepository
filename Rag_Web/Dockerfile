# =============================================================================
# Production Dockerfile for RAG Web Research Assistant
# =============================================================================
# Base image: Python slim (lightweight)
FROM python:3.11-slim

# =============================================================================
# Labels & Metadata
# =============================================================================
LABEL maintainer="DevOps Engineer"
LABEL description="RAG-powered Web Research Assistant with Streamlit"
LABEL version="1.0.0"

# =============================================================================
# Environment Variables
# =============================================================================
# Set Python environment variables for production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# =============================================================================
# Working Directory
# =============================================================================
WORKDIR /app

# =============================================================================
# Install System Dependencies
# =============================================================================
# Required for sentence-transformers and some ML libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Copy Requirements First (for layer caching)
# =============================================================================
# Copy only requirements file first to leverage Docker layer caching
COPY requirements.txt .

# =============================================================================
# Install Python Dependencies
# =============================================================================
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Copy Application Code
# =============================================================================
COPY . .

# =============================================================================
# Create default apy_keys.env if not exists (will be mounted from host)
# =============================================================================
RUN if [ ! -f /app/apy_keys.env ]; then \
    touch /app/apy_keys.env; \
    fi

# =============================================================================
# Create Non-Root User (Security Best Practice)
# =============================================================================
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app \
    && chmod 666 /app/apy_keys.env 2>/dev/null || true

# =============================================================================
# Switch to Non-Root User
# =============================================================================
USER appuser

# =============================================================================
# Expose Streamlit Default Port
# =============================================================================
EXPOSE 8501

# =============================================================================
# Health Check
# =============================================================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501')" || exit 1

# =============================================================================
# Run Command
# =============================================================================
# Streamlit requires --server.headless=true for containerized environments
# --server.address=0.0.0.0 binds to all interfaces
CMD ["streamlit", "run", "streamlit_app.py", "--server.headless=true", "--server.address=0.0.0.0", "--server.port=8501"]