FROM python:3.12-slim

# nodejs/npm e uv (uvx) permitem subir servidores MCP dos dois ecossistemas mais
# comuns (npx @modelcontextprotocol/... e uvx <pacote>) no teste de conexão e na
# descoberta de ferramentas. Sem eles, servidores stdio falham com "comando não
# encontrado".
RUN apt-get update && apt-get install -y --no-install-recommends curl git nodejs npm \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 factory

WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir uv==0.12.1

COPY --chown=factory:factory shared/ shared/
# Apenas os templates de prompt (texto): a API os expõe como ponto de partida
# para customização na tela de configuração de agentes. As definições YAML dos
# agentes NÃO são lidas aqui — a fonte de verdade da API é o banco.
COPY --chown=factory:factory agents/prompts/ agents/prompts/
COPY --chown=factory:factory backend/ backend/
WORKDIR /app/backend
ENV PYTHONPATH=/app:/app/backend

USER factory
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
