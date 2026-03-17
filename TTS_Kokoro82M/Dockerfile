# --- Stage 1: Build Stage ---
FROM python:3.12-slim-bookworm AS builder

# Set environment variables for building
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install build dependencies
# - build-essential: Includes gcc, make, etc.
# - libasound2-dev: Required for building simpleaudio
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libasound2-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install dependencies into a separate directory
# We install everything here to be copied to the final stage
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- Stage 2: Runtime Stage ---
FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLET_SERVER_PORT=8502

WORKDIR /app

# Install runtime system dependencies
# - ffmpeg: Required for audio processing by pydub
# - libasound2: Required for audio output
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy the installed dependencies from the builder stage
COPY --from=builder /install /usr/local

# Create a non-root user for security
RUN useradd -m fletuser && chown -R fletuser:fletuser /app
USER fletuser

# Copy the application code
COPY --chown=fletuser:fletuser . .

# Expose the port Flet will run on
EXPOSE 8502

# Run the application in web mode
CMD ["flet", "run", "src/main.py", "--web", "--port", "8502", "--host", "0.0.0.0"]
