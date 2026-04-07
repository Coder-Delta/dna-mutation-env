FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DNA_ENV_HOST=0.0.0.0 \
    DNA_ENV_PORT=8000 \
    DNA_ENV_WORKERS=1 \
    DNA_ENV_MAX_CONCURRENT_ENVS=8 \
    DNA_ENV_DEFAULT_TASK=easy_snv_short_read \
    DNA_ENV_MAX_STEPS=8 \
    DNA_ENV_LOG_LEVEL=INFO

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install --upgrade pip && \
    pip install .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD sh -c 'curl -fsS http://localhost:${DNA_ENV_PORT}/ready || exit 1'

CMD ["sh", "-c", "python -m uvicorn server.app:app --host 0.0.0.0 --port ${DNA_ENV_PORT}"]
