FROM node:22-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    NODE_PATH=/usr/local/lib/node_modules

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    build-essential cmake git jq ripgrep tree file zip unzip p7zip-full \
    sqlite3 libxml2-utils shellcheck poppler-utils ruby php-cli \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY agent-requirements.txt /tmp/agent-requirements.txt
RUN pip install -r /tmp/agent-requirements.txt \
    && rm /tmp/agent-requirements.txt

RUN npm install -g typescript tsx prettier eslint vitest \
    && npm cache clean --force

WORKDIR /app
COPY pyproject.toml poetry.lock* /app/

RUN python3 -m venv /opt/app-venv \
    && /opt/app-venv/bin/pip install poetry \
    && . /opt/app-venv/bin/activate \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --without dev

COPY src/ /app

RUN useradd --create-home --uid 1001 sandboxuser
USER sandboxuser

ENV PIP_NO_INDEX=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    npm_config_offline=true

EXPOSE 8000

CMD ["/opt/app-venv/bin/uvicorn", "--app-dir", "/app", "sandbox.app:app", "--host", "0.0.0.0", "--port", "8000"]