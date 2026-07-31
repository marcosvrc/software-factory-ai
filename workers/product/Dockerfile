FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 factory

WORKDIR /app
COPY workers/requirements.txt ./worker-requirements.txt
RUN pip install --no-cache-dir -r worker-requirements.txt

COPY --chown=factory:factory shared/ shared/
COPY --chown=factory:factory agents/ agents/
COPY --chown=factory:factory tools/ tools/
COPY --chown=factory:factory workers/ workers/
COPY --chown=factory:factory sandbox/ sandbox/

USER factory
