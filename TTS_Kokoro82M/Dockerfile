# Versione semplificata per Flet in modalità Web
FROM python:3.12-slim-bookworm

# Variabili d'ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLET_SERVER_PORT=8502 \
    PATH="/home/fletuser/.local/bin:${PATH}"

WORKDIR /app

# Installiamo ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m fletuser

# Copiamo i requisiti e installiamo forzando l'installazione di sistema (necessario in Debian Bookworm)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --break-system-packages && \
    python -m pip show flet-cli && \
    python -m flet --version

# Copiamo il resto del codice e cambiamo i permessi
COPY . .
RUN chown -R fletuser:fletuser /app

# Passiamo all'utente non-root
USER fletuser

EXPOSE 8502

# Avviamo Flet in modalità Web tramite il modulo python per evitare problemi di path
CMD ["python", "-m", "flet", "run", "src/main.py", "--web", "--port", "8502", "--host", "0.0.0.0"]
