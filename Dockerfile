FROM python:3.11-slim

ENV FLASK_APP="src:create_app()"
ENV FLASK_ENV=development
ENV POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        gcc \
        python3-dev \
        libffi-dev \
        && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry \
    && useradd -m appuser

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

COPY src/ src/

RUN chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5004/api/status || exit 1

CMD ["poetry", "run", "flask", "run", "--host=0.0.0.0", "--port=5004"]