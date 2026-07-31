# Software Factory — Fábrica de Software Local Multiagente

Implementação da **Proposta de Arquitetura Local Multiagente para uma Fábrica de Software** (v1.0).

- **Execução:** local, com Docker Compose
- **Linguagem:** Python 3.12+
- **Orquestração de agentes:** LangGraph
- **Modelo de linguagem local:** Ollama (no host)
- **Licença:** Apache-2.0

## Arquitetura

O fluxo não é uma conversa livre entre agentes: é controlado por um orquestrador com estados
explícitos, tarefas persistidas, transições condicionais, filas por domínio, rastreabilidade,
limites de repetição, aprovação humana, artefatos versionados e sandbox de execução.

| Camada | Tecnologia |
|---|---|
| Apresentação | Next.js (`frontend/`) |
| API | FastAPI (`backend/`) |
| Orquestração | LangGraph (`orchestrator/`) |
| Execução | Workers por domínio (`workers/`) |
| Modelo | Ollama no host |
| Dados | PostgreSQL, Redis, RabbitMQ, MinIO, Git |
| Observabilidade | Langfuse, OpenTelemetry, Prometheus, Grafana, Loki |

## Agentes

Todos os papéis da fábrica existem como **agentes lógicos** definidos em YAML
(`agents/definitions/`), agrupados em 8 workers físicos por domínio: product, architecture,
engineering, validation, security, operations, delivery e governance.

## Pré-requisitos

- Docker Desktop + Docker Compose
- Git e Make
- Ollama no host

```bash
ollama pull qwen2.5-coder:7b
ollama pull llama3.1:8b
```

## Inicialização

```bash
cp .env.example .env
docker compose up -d postgres redis rabbitmq minio
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m app.db.seed
docker compose up -d
```

Com Langfuse (observabilidade de LLM):

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
```

## Endereços locais

| Serviço | Endereço |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| RabbitMQ | http://localhost:15672 |
| MinIO | http://localhost:9001 |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |
| Langfuse | http://localhost:3002 |
| Ollama | http://localhost:11434 |

## Comandos Make

`make setup | up | down | logs | test | lint | format | typecheck | security | migrate | migration name=... | seed | clean`

## Fluxo de trabalho

Demanda → Triagem → Produto/Descoberta → Requisitos → *Aprovação de escopo* → Arquitetura →
*Architecture gate* → Planejamento técnico → Desenvolvimento → Code review → Testes →
QA funcional → Segurança → Validação operacional → Documentação/Release → *Aprovação humana* → Entrega.

Máximo de **3 ciclos automáticos por gate**; após o terceiro, o item vai para
`HUMAN_REVIEW_REQUIRED`. Documentação detalhada em `docs/`.
