FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 factory

WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=factory:factory shared/ shared/
COPY --chown=factory:factory backend/ backend/
WORKDIR /app/backend
ENV PYTHONPATH=/app:/app/backend

USER factory
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
