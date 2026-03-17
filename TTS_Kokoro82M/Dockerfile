# Build Version: 3.0 (User-mode installation)
FROM python:3.12-slim-bookworm

# Variabili d'ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLET_SERVER_PORT=8502 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/home/fletuser/.local/bin:${PATH}"

WORKDIR /app

# Installiamo ffmpeg come root
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m fletuser && \
    chown fletuser:fletuser /app

# Passiamo subito all'utente non-root per l'installazione
USER fletuser

# Pulizia preventiva della cache pip locale dell'utente
RUN pip cache purge || true

# Copiamo i requisiti e installiamo in user-mode
COPY --chown=fletuser:fletuser requirements.txt .
RUN pip install --user --upgrade pip && \
    pip install --user -r requirements.txt && \
    python -m flet --version  # Deve mostrare la versione correttamente

# Copiamo il resto del codice
COPY --chown=fletuser:fletuser . .

EXPOSE 8502

# Avviamo Flet in modalità Web
CMD ["python", "-m", "flet", "run", "src/main.py", "--web", "--port", "8502", "--host", "0.0.0.0"]
