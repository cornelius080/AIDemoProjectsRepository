# Use a lightweight, modern Python image
# Slim version based on Debian Bookworm is preferred for production
FROM python:3.12-slim-bookworm

# Set environment variables
# - PYTHONUNBUFFERED: Ensures output is sent directly to terminal without buffering
# - PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files
# - FLET_SERVER_PORT: Default port for Flet web server
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLET_SERVER_PORT=8502

# Set working directory
WORKDIR /app

# Install system dependencies
# - ffmpeg: Required for audio processing by pydub
# - libasound2: Required for audio output by simpleaudio
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security and set ownership
RUN useradd -m fletuser && chown -R fletuser:fletuser /app
USER fletuser

# Copy requirements first to leverage Docker layer caching
COPY --chown=fletuser:fletuser requirements.txt .

# Install Python dependencies
# Using --no-cache-dir to keep the image small
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY --chown=fletuser:fletuser . .

# Expose the port Flet will run on
EXPOSE 8502

# Run the application in web mode
# --web: Forces Flet to run as a web server
# --port: Specifies the port to listen on
# --host: Listen on all interfaces
CMD ["flet", "run", "src/main.py", "--web", "--port", "8502", "--host", "0.0.0.0"]
