# Use a lightweight base image as requested
FROM python:3.11-slim-bookworm

# Set metadata
LABEL maintainer="Expert DevOps Engineer"
LABEL description="Production-ready Dockerfile for GeminiVoiceAgent"

# Avoid writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for pyaudio and other potential python builds
# - gcc, python3-dev: needed to compile C extensions
# - portaudio19-dev, libportaudio2, libasound-dev: needed for pyaudio
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
# Using --no-cache-dir to keep the image small
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user to run the application for better security
RUN useradd -m -r appuser && \
    chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Copy the rest of the application files
# We do this after pip install to avoid cache invalidation when code changes
COPY --chown=appuser:appuser . .

# Ensure frontend directory exists (copied over) and has correct permissions
# It contains the static files that fastapi will serve

# Expose the application port (inferred from main.py:8000)
EXPOSE 8000

# Define the command to start the server
# Using uvicorn to run the FastAPI app on 0.0.0.0 and port 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
