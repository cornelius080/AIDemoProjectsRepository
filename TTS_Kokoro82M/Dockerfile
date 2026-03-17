# Versione semplificata per Flet in modalità Web
FROM python:3.12-slim-bookworm

# Variabili d'ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLET_SERVER_PORT=8502

WORKDIR /app

# Installiamo solo ffmpeg per pydub (non serve gcc senza simpleaudio)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Creiamo l'utente PRIMA di installare le dipendenze se vogliamo installarle a livello di sistema
# o DOPO se usiamo --user. Qui installiamo a livello di sistema come root e poi passiamo all'utente.
RUN useradd -m fletuser

# Copiamo i requisiti e installiamo
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m flet --version  # Verifica che il CLI sia installato e pronto

# Copiamo il resto del codice e cambiamo i permessi
COPY . .
RUN chown -R fletuser:fletuser /app

# Passiamo all'utente non-root
USER fletuser

EXPOSE 8502

# Avviamo Flet in modalità Web tramite il modulo python per evitare problemi di path
CMD ["python", "-m", "flet", "run", "src/main.py", "--web", "--port", "8502", "--host", "0.0.0.0"]
