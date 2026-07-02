# Use a lightweight base image
FROM python:3.11-slim-bookworm

# Set environment variables
# PYTHONUNBUFFERED=1: ensures Python output is logged to the terminal
# FLET_SERVER_PORT=8080: used by Flet
# DOCKER_RUNNING=true: signals the app to bind to 0.0.0.0 and start on the web
ENV PYTHONUNBUFFERED=1 \
    FLET_SERVER_PORT=8080 \
    DOCKER_RUNNING=true

# Set the working directory
WORKDIR /app

# Install system dependencies
# gcc, portaudio19-dev, and python3-dev are required to build and run PyAudio
# ffmpeg is used by HuggingFace Transformers/Whisper to process audio
# alsa-utils and libportaudio2 are for audio hardware interaction
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libportaudio2 \
    portaudio19-dev \
    gcc \
    python3-dev \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m asruser

# Create necessary directories for volumes and ensure correct permissions
RUN mkdir -p downloads uploads storage && \
    chown -R asruser:asruser /app

# Copy requirements file to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
# Upgrade pip and install from requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --break-system-packages

# Copy the rest of the application code
COPY . .

# Ensure the new files are owned by the non-root user
RUN chown -R asruser:asruser /app

# Define volumes for the application
VOLUME ["/app/downloads", "/app/uploads", "/app/storage"]

# Switch to the non-root user for security
USER asruser

ENV PATH="/home/asruser/.local/bin:${PATH}"

# Expose the port the app runs on
EXPOSE 8080

# Define the run command to start the application
CMD ["python", "src/main.py"]
