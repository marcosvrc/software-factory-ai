# Imagem aprovada do sandbox (seção 16.2): ferramentas determinísticas de
# lint, tipos, testes e scanners, sem acesso a rede em tempo de execução.
FROM python:3.12-slim

RUN pip install --no-cache-dir \
    pytest pytest-asyncio ruff mypy bandit pip-audit radon \
    && useradd -m -u 1000 sandbox

USER sandbox
WORKDIR /workspace
