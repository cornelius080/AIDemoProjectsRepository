# Build Version: 5.0 (Flet-web fix)
FROM python:3.12-slim-bookworm

# Variabili d'ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DOCKER_RUNNING=true

WORKDIR /app

# Installiamo ffmpeg per pydub
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m fletuser

# Installiamo le dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --break-system-packages

# Copiamo il codice
COPY . .
RUN chown -R fletuser:fletuser /app

# Passiamo all'utente non-root
USER fletuser
EXPOSE 8080

# Avviamo direttamente lo script Python (non serve flet-cli)
CMD ["python", "src/main.py"]
