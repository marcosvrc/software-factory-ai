FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 factory

WORKDIR /app
COPY orchestrator/requirements.txt ./orchestrator-requirements.txt
RUN pip install --no-cache-dir -r orchestrator-requirements.txt

COPY --chown=factory:factory shared/ shared/
COPY --chown=factory:factory agents/ agents/
COPY --chown=factory:factory tools/ tools/
COPY --chown=factory:factory orchestrator/ orchestrator/

USER factory
CMD ["python", "-m", "orchestrator.main"]
