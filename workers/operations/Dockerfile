FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 factory

WORKDIR /app
COPY workers/requirements.txt ./worker-requirements.txt
RUN pip install --no-cache-dir -r worker-requirements.txt

COPY shared/ shared/
COPY agents/ agents/
COPY tools/ tools/
COPY workers/ workers/
COPY sandbox/ sandbox/

USER factory
