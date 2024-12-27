FROM python:3.11-slim

ENV FLASK_APP="src:create_app()"
ENV FLASK_ENV=development

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        gcc \
        python3-dev \
        libffi-dev \
        && rm -rf /var/lib/apt/lists/*\
        && useradd -m appuser

COPY requirements.dev.txt .
RUN pip install --no-cache-dir -r requirements.dev.txt

COPY src/ src/

RUN chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5004/api/status || exit 1

CMD ["flask", "run", "--host=0.0.0.0", "--port=5004"]