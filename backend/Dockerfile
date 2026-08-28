FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app


RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock* /app/

RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root

COPY src/ /app
COPY logging.json /app/logging.json

EXPOSE 8000

CMD ["uvicorn", "lad.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "logging.json"]