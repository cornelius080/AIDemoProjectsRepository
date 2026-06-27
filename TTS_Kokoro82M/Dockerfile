# -- Builder Stage --
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install build tools required for compiling some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment to safely install dependencies 
# This avoids PEP 668 externally managed environment issues without needing --break-system-packages
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# -- Final Runtime Stage --
FROM python:3.12-slim-bookworm

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    FLET_SERVER_PORT=8080 \
    DOCKER_RUNNING=true \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install runtime system dependencies (ffmpeg for audio processing, curl for docker-compose healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/bash fletuser

# Setup directories for volumes and apply correct ownership
RUN mkdir -p /app/downloads /app/uploads && \
    chown -R fletuser:fletuser /app

# Copy the compiled virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application source code with the correct permissions in one step
COPY --chown=fletuser:fletuser . .

# Explicitly define volumes
VOLUME ["/app/downloads", "/app/uploads"]

# Drop privileges to the non-root user for security
USER fletuser
EXPOSE 8080

# Start the application directly
CMD ["python", "src/main.py"]
