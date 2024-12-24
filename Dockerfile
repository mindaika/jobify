FROM python:3.11-slim

WORKDIR /app
COPY requirements.dev.txt .
RUN pip install --no-cache-dir -r requirements.dev.txt

COPY src/ src/

ENV FLASK_APP="src:create_app()"
ENV FLASK_ENV=development

CMD ["flask", "run", "--host=0.0.0.0", "--port=5004"]