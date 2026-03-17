FROM python:3.12-slim

WORKDIR /app

# Install dependencies using pip
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY . .

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}
ENV DOCKER_RUNNING=true

EXPOSE 8080

CMD ["python", "src/main.py"]