# Build Version: 6.4 (Corrected FilePicker API)
FROM python:3.12-slim-bookworm

# Variabili d'ambiente
ENV PYTHONUNBUFFERED=1 \
    FLET_SERVER_PORT=8080 \
    FLET_SECRET_KEY="flet_secret_key_placeholder" \
    DOCKER_RUNNING=true

WORKDIR /app

# Installiamo ffmpeg per pydub
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m fletuser

# Prepariamo le directory per i volumi
RUN mkdir -p downloads uploads && \
    chown -R fletuser:fletuser /app

# Installiamo le dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --break-system-packages

# Copiamo il codice
COPY . .
RUN chown -R fletuser:fletuser /app

# Definizione volumi
VOLUME ["/app/downloads", "/app/uploads"]

# Passiamo all'utente non-root
USER fletuser
EXPOSE 8080

# Avviamo direttamente lo script Python (non serve flet-cli)
CMD ["python", "src/main.py"]
