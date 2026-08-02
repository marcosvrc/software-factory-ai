# Software Factory — Fábrica de Software Local Multiagente

Implementação da **Proposta de Arquitetura Local Multiagente para uma Fábrica de Software** (v1.0).

- **Execução:** local, com Docker Compose
- **Linguagem:** Python 3.12+ (backend/orquestração) e Node.js 20 (frontend)
- **Orquestração de agentes:** LangGraph
- **Modelo de linguagem local:** Ollama (executado no host, não em container)
- **Licença:** Apache-2.0

## Índice

- [Visão geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Fluxo de trabalho](#fluxo-de-trabalho)
- [Agentes](#agentes)
- [Interface web](#interface-web)
- [Configuração de agentes](#configuração-de-agentes)
- [Servidores MCP](#servidores-mcp)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Pré-requisitos](#pré-requisitos)
- [Como rodar](#como-rodar)
- [Comandos Make](#comandos-make)
- [Endereços locais](#endereços-locais)
- [Usuários padrão (seed)](#usuários-padrão-seed)
- [Observabilidade](#observabilidade)
- [Resiliência do orquestrador](#resiliência-do-orquestrador)
- [Documentação adicional](#documentação-adicional)

## Visão geral

O projeto simula uma fábrica de software onde uma demanda percorre um pipeline de estados
explícitos — da triagem inicial até a entrega — sendo processada por **agentes de IA
especializados**, cada um representando um papel real de uma organização de desenvolvimento
(Product Manager, Arquiteto de Solução, Desenvolvedor Backend, QA, AppSec, SRE, etc.).

O fluxo **não é uma conversa livre entre agentes**. Ele é controlado por um orquestrador com:

- estados explícitos e persistidos (projeto, execução, tarefa, aprovação);
- transições condicionais e validadas (transições inválidas são rejeitadas);
- filas de trabalho por domínio (RabbitMQ);
- rastreabilidade completa (auditoria, artefatos versionados);
- limite de repetição por gate (máximo de 3 ciclos automáticos);
- aprovação humana obrigatória em pontos críticos;
- sandbox de execução para código gerado pelos agentes.

## Arquitetura

| Camada | Tecnologia | Diretório |
|---|---|---|
| Apresentação | Next.js 14 + Tailwind CSS + React Flow | `frontend/` |
| API | FastAPI | `backend/` |
| Orquestração | LangGraph | `orchestrator/` |
| Execução dos agentes | Workers por domínio | `workers/` |
| Definições de agentes | YAML declarativo | `agents/definitions/` |
| Ferramentas dos agentes | Tools tipadas | `tools/` |
| Sandbox de código | Containers efêmeros | `sandbox/` |
| Contratos compartilhados | Pydantic / dataclasses | `shared/` |
| Integração MCP | Cliente JSON-RPC + OAuth 2.1 | `shared/mcp/` |
| Modelo de linguagem | Ollama (no host) | — |
| Dados | PostgreSQL, Redis, RabbitMQ, MinIO, Git | — |
| Observabilidade | OpenTelemetry, Prometheus, Grafana, Loki | `infrastructure/` |

Cada agente lógico (papel) é definido declarativamente em YAML — objetivo, entradas/saídas
esperadas, ferramentas permitidas e negadas, modelo utilizado, gates de qualidade e política de
escalonamento. Os agentes são agrupados em **8 workers físicos** por domínio, que consomem
mensagens do RabbitMQ e usam o Ollama local para inferência.

## Fluxo de trabalho

```
Demanda → Triagem → Análise de intake → Produto/Descoberta → Requisitos →
[Aprovação de escopo] → Arquitetura → [Architecture gate] → Planejamento técnico →
Desenvolvimento → Code review → Testes → QA funcional → Segurança →
Validação operacional → Documentação/Release → [Aprovação humana] → Entrega
```

- **Análise de intake:** antes de gastar ciclos de produto e arquitetura, o agente
  `product.intake-analyst` avalia se a demanda tem informação suficiente (canal de acesso,
  escopo, volume esperado, regras de negócio essenciais, restrições não-funcionais, dados
  sensíveis, integrações e critérios de sucesso). Diferente dos outros gates, quando falta
  informação o fluxo **pergunta ao solicitante** em vez de tentar adivinhar: é criada uma
  aprovação do tipo `intake_clarification` e a resposta dada no campo de justificativa é
  reinjetada na próxima análise (`clarification_notes`).
- **Máximo de 3 ciclos automáticos por gate.** Após a terceira tentativa falha, o item muda para
  `HUMAN_REVIEW_REQUIRED` e aguarda intervenção humana. Aprovar a revisão humana **zera os
  contadores** e retoma a execução na etapa seguinte ao gate que escalou (nunca do zero, nem
  pulando etapas).
- **Findings são por etapa, não cumulativos.** Cada etapa substitui os seus próprios findings a
  cada rodada. Sem isso, um problema já corrigido continuava sendo reapresentado ao modelo como
  se fosse atual, prendendo a demanda em loop indefinido.
- Os estados de projeto, execução (`run`) e tarefa (`task`) seguem máquinas de estado explícitas
  com transições validadas (`shared/contracts/states.py`). Transições fora da tabela permitida
  geram `InvalidTransitionError`.
- Toda transição de estado gera um evento de auditoria; cancelamento não apaga histórico nem
  artefatos.

Documentação detalhada do fluxo e das decisões arquiteturais em [`docs/`](docs/) e nos
[ADRs](docs/adrs/).

## Agentes

Todos os papéis da fábrica existem como **agentes lógicos** declarados em YAML
(`agents/definitions/<domínio>/<agente>.yaml`) e registrados em `agents/registry.yaml`. Cada
definição especifica objetivo, responsabilidades, entradas/saídas, artefatos gerados, ferramentas
permitidas/negadas, modelo de LLM (primário e fallback), gates de qualidade, política de retry e
escalonamento.

Os 54 agentes lógicos são agrupados em **8 workers físicos** por domínio:

### Product (`workers/product`)

| Agente | Objetivo | Principais artefatos |
|---|---|---|
| Analista de Intake | Avalia se a demanda tem informação suficiente para iniciar o desenvolvimento e pergunta ao solicitante o que falta | `product/intake-checklist.md` |
| Product Manager | Define visão de produto, valor esperado e métricas da demanda | `product/vision.md`, `product/metrics.md` |
| Product Owner | Prioriza backlog, esclarece objetivos e valida aceite de negócio | `product/backlog-priorities.md` |
| Analista de Negócios | Identifica regras de negócio, modela processos e mapeia atores | `product/business-rules.md`, `product/process-model.mmd` |
| Analista de Requisitos | Cria histórias testáveis com critérios de aceite e RNFs | `requirements/user-stories.md`, `requirements/nfrs.md` |
| UX Researcher | Cria hipóteses sobre usuários e registra riscos de usabilidade | `ux/research-hypotheses.md` |
| UX/UI Designer | Cria fluxos, wireframes e componentes verificando acessibilidade | `ux/user-flows.mmd`, `ux/wireframes.md` |

### Architecture (`workers/architecture`)

| Agente | Objetivo | Principais artefatos |
|---|---|---|
| Arquiteto de Solução | Produz arquitetura coerente com requisitos e restrições; registra ADRs | `architecture/solution-architecture.md`, `architecture/adrs/` |
| Arquiteto de Software | Define módulos, interfaces internas e regras de dependência | `architecture/modules.md` |
| Arquiteto de Dados | Define modelos de dados, persistência, retenção e migração | `architecture/data-model.md` |
| Arquiteto de Integração | Define APIs, eventos, contratos, versionamento e idempotência | `architecture/integration.md`, `architecture/api-contracts.md` |
| Arquiteto de Segurança | Define trust boundaries, cria threat model e controles | `architecture/threat-model.md` |
| Governança de Arquitetura | Verifica conformidade com padrões e identifica dívida arquitetural | `architecture/governance-report.md` |
| Tech Lead | Transforma arquitetura em tarefas técnicas e orienta implementação | `planning/technical-backlog.md` |

### Engineering (`workers/engineering`)

| Agente | Objetivo | Principais artefatos |
|---|---|---|
| Desenvolvedor Backend | Implementa serviços, regras de negócio, APIs, persistência e testes | `code/patch.diff`, `code/tests/` |
| Desenvolvedor Frontend | Implementa interface com acessibilidade e integração com APIs | `code/frontend-patch.diff` |
| Desenvolvedor Mobile | Implementa aplicações móveis, permissões e armazenamento local | `code/mobile-patch.diff` |
| Engenheiro de Integração | Implementa conectores, contratos, consumidores/produtores de eventos | `code/integration-patch.diff` |
| Engenheiro de Dados | Implementa pipelines, transformações e validação de qualidade | `code/data-pipeline-patch.diff` |
| Revisor de Código | Revisa legibilidade, aderência à arquitetura, testes e segurança básica | `review/code-review-report.md` |
| Agente de Refatoração | Identifica duplicação/complexidade e propõe melhorias sem alterar comportamento | `review/refactoring-proposals.md` |

### Validation (`workers/validation`)

| Agente | Objetivo | Principais artefatos |
|---|---|---|
| QA Lead | Define estratégia de qualidade e consolida o parecer de QA | `qa/qa-verdict.md` |
| QA Funcional | Deriva cenários, executa validações e registra defeitos | `qa/functional-test-report.md` |
| Automação de Testes | Cria testes de API, integração, interface e regressão | `qa/automation-report.md` |
| Testes de Performance | Cria cenários de carga, mede latência e identifica gargalos | `qa/performance-report.md` |
| Acessibilidade | Verifica WCAG, navegação por teclado, semântica e contraste | `qa/accessibility-report.md` |
| Dados de Teste | Cria massa sintética, mascara dados e garante cobertura | `qa/test-data-manifest.md` |
| Avaliação de IA | Cria datasets de avaliação e mede qualidade/alucinação de componentes de IA | `qa/ai-eval-report.md` |

### Security (`workers/security`)

| Agente | Objetivo | Principais artefatos |
|---|---|---|
| AppSec | Executa SAST, revisa autenticação e identifica vulnerabilidades | `security/appsec-report.md` |
| DevSecOps | Integra scanners ao pipeline e define gates de segurança | `security/devsecops-report.md` |
| Privacidade | Identifica dados pessoais e avalia minimização/retenção/consentimento | `security/privacy-assessment.md` |
| Conformidade | Verifica políticas, requisitos regulatórios e rastreabilidade | `security/compliance-report.md` |
| Jurídico | Avalia termos, licenças, contratos e propriedade intelectual | `security/legal-assessment.md` |
| Open Source e Licenciamento | Cria SBOM e verifica licenças/incompatibilidades | `security/sbom.json`, `security/license-report.md` |
| Segurança de IA | Avalia prompt injection, vazamento de dados e abuso de ferramentas | `security/ai-security-report.md` |

### Operations (`workers/operations`)

| Agente | Objetivo | Principais artefatos |
|---|---|---|
| DevOps | Cria pipeline automatizando build, testes, empacotamento e release | `operations/pipeline.md` |
| Engenheiro de Plataforma | Cria templates, ambientes e catálogos; melhora DX | `operations/platform-templates.md` |
| Infraestrutura | Define recursos, redes, volumes e IaC | `operations/infrastructure.md` |
| Gestão de Configuração | Controla versões, parâmetros, feature flags e compatibilidade | `operations/configuration.md` |
| DBA / Database Reliability | Otimiza consultas/índices e garante backup e disponibilidade | `operations/database-review.md` |
| SRE | Define SLI/SLO, dashboards, alertas, runbooks e resiliência | `operations/slo.md`, `operations/runbook.md` |
| FinOps | Estima consumo e custo de inferência/execução; propõe otimizações | `operations/finops-report.md` |
| Gestão de Ambientes | Verifica disponibilidade, consistência e dependências de ambientes | `operations/environments-report.md` |

### Delivery (`workers/delivery`)

| Agente | Objetivo | Principais artefatos |
|---|---|---|
| Release Manager | Verifica aprovações, consolida release notes e valida rollback | `release/release-notes.md`, `release/rollback-plan.md` |
| Change Manager | Classifica mudanças, avalia impacto e registra aprovação | `release/change-record.md` |
| Incident Manager | Coordena incidentes, classifica severidade e mantém timeline | `operations/incident-timeline.md` |
| Problem Manager | Investiga recorrência, conduz causa raiz e ações preventivas | `operations/problem-analysis.md` |
| Suporte Técnico | Classifica chamados, consulta base de conhecimento e escala | `support/ticket-analysis.md` |
| Documentação Técnica | Mantém README, guias, diagramas e documentação de APIs | `docs/README.md`, `docs/api.md` |
| Developer Experience | Simplifica setup, reduz tempo de build e cria templates | `docs/devex-improvements.md` |

### Governance (`workers/governance`)

| Agente | Objetivo | Principais artefatos |
|---|---|---|
| Engineering Manager | Avalia capacidade dos workers e prioriza tarefas técnicas | `governance/engineering-plan.md` |
| Flow Manager / Scrum Master | Acompanha fluxo, identifica bloqueios e controla WIP | `governance/flow-report.md` |
| Gestor de Portfólio | Prioriza projetos e consolida indicadores de benefício/custo | `governance/portfolio-report.md` |
| Gestor de Riscos | Mantém registro de riscos e escala riscos críticos | `governance/risk-register.md` |

### Convenções comuns a todos os agentes

- **Modelo:** todos usam Ollama local, com modelo primário e fallback (`qwen2.5-coder:7b` para
  tarefas de código/arquitetura, `llama3.1:8b` para tarefas analíticas/textuais).
- **Ferramentas negadas por padrão:** `shell.unrestricted`, `production.deploy`, `secrets.read` —
  nenhum agente tem acesso irrestrito a shell, deploy em produção ou segredos.
- **Retry:** no máximo 2 tentativas automáticas; ao falhar, o item vai para revisão humana
  (`human_review`).
- **Escalonamento:** cada agente declara para quem escalar (ex.: `tech-lead`,
  `human-architect`, `human-security`) quando não consegue resolver.
- **Saída padronizada:** todo agente retorna um `AgentResult` validado contra
  `agents/schemas/agent-result.schema.json`. Quando produz código, preenche `code_files` com o
  conteúdo completo dos arquivos — que é persistido no MinIO, registrado na tabela `artifacts` e
  materializado em `workspaces/<project_id>/` para você abrir num editor normal.

## Interface web

| Tela | Rota | O que faz |
|---|---|---|
| Painel | `/` | Visão geral: projetos, aprovações pendentes, agentes habilitados |
| Monitor | `/monitor` | Todas as execuções em tempo real (atualiza a cada 5s), com filtros e esteira de progresso |
| Projetos | `/projects` | Cria projetos e demandas e dispara execuções |
| Aprovações | `/approvals` | Decide aprovações humanas (escopo, release, esclarecimento de intake, revisão por limite de ciclos) |
| Execução | `/runs/{id}` | Detalhe da execução: diagrama do processo, tarefas, artefatos (com download) e timeline |
| Agentes | `/agents` | Habilita/desabilita agentes e configura objetivo, modelo, ferramentas e prompt |
| MCP | `/mcp` | Cadastra servidores MCP, autoriza via OAuth e descobre as ferramentas expostas |

O detalhe da execução traz um **diagrama do processo no estilo Camunda Cockpit** (React Flow),
desenhando as 15 etapas e os caminhos reais do grafo — fluxo normal, ciclos de ajuste, escaladas
para revisão humana e retomada — com o ponto atual da execução destacado e o contador de ciclos
(`N/3`) em cada gate.

## Configuração de agentes

A configuração efetiva de cada agente vive no **banco** (tabela `agent_definitions`) e é o que o
orquestrador e os workers realmente aplicam ao executar. Os YAMLs em `agents/definitions/` são a
semente: na primeira sincronização eles populam a configuração e ficam guardados como
`default_configuration`, usada pelo botão **Restaurar padrão**.

Pela tela `/agents` (papel `FACTORY_MANAGER` ou superior) é possível:

- **habilitar/desabilitar** um agente — desabilitado, ele é ignorado nas próximas execuções e a
  etapa segue com os demais agentes (se todos estiverem desabilitados, a etapa é aprovada
  automaticamente em vez de travar o fluxo);
- editar **objetivo**, **responsabilidades** e **critérios de qualidade**;
- trocar **modelo** primário/fallback, temperatura e janela de contexto;
- ajustar **ferramentas** permitidas e negadas;
- definir um **prompt próprio** por agente (em branco, usa o template base compartilhado). Os
  placeholders disponíveis são `{agent_name}`, `{agent_version}`, `{objective}`,
  `{responsibilities}`, `{input_manifest}`, `{constraints}`, `{allowed_tools}` e
  `{quality_gates}`;
- vincular **servidores MCP** ao agente.

Mudanças valem para **novas** execuções, com janela de até ~10s de cache
(`AGENT_CONFIG_CACHE_TTL_SECONDS`). Execuções em andamento seguem com a configuração que
carregaram. Uma configuração inválida é rejeitada pela API; se ainda assim algo ficar
inconsistente, o runtime volta para o YAML base em vez de derrubar o pipeline.

## Servidores MCP

A tela `/mcp` (papel `ADMIN`) cadastra servidores [MCP](https://modelcontextprotocol.io) e
descobre as ferramentas que eles expõem. Dois transportes são suportados:

- **stdio** — o servidor sobe como subprocesso (`npx`, `uvx`, `node`, `python3` estão disponíveis
  na imagem da API). Credenciais vão em variáveis de ambiente.
- **http** — MCP Streamable HTTP, com autenticação via header estático **ou OAuth 2.1**.

Para servidores OAuth (como o MCP hospedado do Notion, que não aceita token estático), o botão
**Autorizar** executa o fluxo completo: descoberta da Protected Resource Metadata (RFC 9728) e da
metadata do authorization server (RFC 8414/OIDC), registro dinâmico de cliente (RFC 7591),
authorization code com **PKCE S256** e o parâmetro `resource` (RFC 8707), e renovação automática
do token quando expira.

> **Segurança:** um servidor stdio é um comando arbitrário executado no container da API — quem
> cadastra consegue, por definição, executar código ali. Por isso a criação exige papel `ADMIN`,
> servidores **nascem desabilitados**, o subprocesso **não herda o ambiente do container** (recebe
> apenas `PATH`/`HOME`/`LANG` e as variáveis declaradas) e valores de `env`/`headers`, tokens e
> `client_secret` **nunca são devolvidos pela API** — só as chaves e o estado da autorização.

Se você acessar a fábrica por um endereço diferente de `http://localhost:8000`, ajuste
`MCP_OAUTH_REDIRECT_URI`: o redirect URI é registrado no provedor e precisa bater exatamente.

**Estado atual:** os agentes ainda não invocam ferramentas MCP durante as execuções — esta fase
cobre configuração, autorização e descoberta. A execução automática (loop de tool calling no
runtime) é o próximo passo.

## Estrutura do repositório

```
.
├── agents/            # Definições declarativas (YAML) e runtime dos agentes
│   ├── definitions/    #   agrupadas por domínio (product, architecture, engineering, ...)
│   ├── prompts/        #   prompt base compartilhado
│   ├── runtime/        #   executor e client Ollama
│   └── schemas/        #   JSON Schemas de validação de saída
│   └── config_store.py #   configuração efetiva dos agentes (banco sobre YAML)
├── orchestrator/      # Grafos LangGraph, roteamento, checkpoints e estado
├── workers/           # 8 workers físicos (1 processo por domínio), consumindo RabbitMQ
├── backend/           # API FastAPI (auth, projetos, runs, aprovações, artefatos, agentes, MCP)
│   └── migrations/     #   migrações Alembic
├── frontend/          # Next.js: design system próprio + telas da fábrica
│   └── src/
│       ├── app/        #     rotas (painel, monitor, projetos, aprovações, agentes, mcp, runs)
│       ├── components/ #     ui/ (design system), domain/ (pipeline, diagrama), layout/
│       └── lib/        #     client da API, permissões, mapas de status
├── shared/            # Contratos (Pydantic/dataclasses), logging, utils compartilhados
│   └── mcp/            #   cliente MCP (JSON-RPC stdio/HTTP) + OAuth 2.1
├── workspaces/        # Código gerado pelos agentes (cópia local navegável; fora do Git)
├── tools/             # Ferramentas tipadas usadas pelos agentes (git, db, containers, etc.)
├── sandbox/           # Política e runner de execução sandboxed de código gerado
├── infrastructure/    # Configs de Grafana, Prometheus, Loki, OTel, RabbitMQ, MinIO
├── docs/              # Documentação de arquitetura, ADRs, operações, segurança e API
├── tests/             # Testes de integração, e2e, performance e segurança
└── docker-compose.yml
```

## Pré-requisitos

- Docker Desktop, Rancher Desktop ou equivalente (com Docker Compose v2)
- Git e Make
- Ollama instalado e rodando no host (**não** roda em container)

```bash
ollama pull qwen2.5-coder:7b
ollama pull llama3.1:8b
ollama serve   # se ainda não estiver rodando como serviço
```

> Recomendação de recursos para a VM/daemon do Docker (Docker Desktop, Rancher Desktop, etc.):
> pelo menos **8GB de RAM e 4 CPUs**, já que o stack completo sobe ~19 containers (infra +
> API + orquestrador + 8 workers + frontend + observabilidade). Em máquinas Apple Silicon,
> prefira o backend de virtualização `vz` em vez de `qemu`.

## Como rodar

### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Ajuste `.env` se necessário (portas, credenciais, modelos). Os valores padrão já funcionam para
uso local.

### 2. Subir a infraestrutura de dados

```bash
docker compose up -d postgres redis rabbitmq minio
```

Aguarde os 4 serviços ficarem `healthy` (`docker compose ps`).

### 3. Rodar migrações e seed

```bash
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m app.db.seed
```

O seed cria os usuários padrão descritos em [Usuários padrão](#usuários-padrão-seed).

> As migrações incluem o esquema inicial (`0001`), a configuração editável de agentes (`0002`) e
> os servidores MCP com autorização OAuth (`0003`, `0004`). Ao atualizar um ambiente existente,
> rode `alembic upgrade head` antes de subir a API.

### 4. Subir o restante do stack

```bash
docker compose up -d
```

Isso inicia a API, o orquestrador, os 8 workers de domínio, o frontend e a stack de
observabilidade (Prometheus, Grafana, Loki, OTel Collector).

> Em máquinas com recursos limitados, prefira subir por etapas em vez de tudo de uma vez:
> `docker compose up -d api` → aguardar `healthy` → `docker compose up -d orchestrator
> product-worker architecture-worker engineering-worker validation-worker security-worker
> operations-worker delivery-worker governance-worker` → `docker compose up -d frontend
> otel-collector prometheus loki grafana`.

### 5. Verificar

```bash
docker compose ps
curl http://localhost:8000/health
```

Acesse o frontend em http://localhost:3000 e a documentação interativa da API em
http://localhost:8000/docs.

### Com observabilidade de LLM (Langfuse)

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
```

### Encerrar

```bash
docker compose down          # mantém volumes (dados persistidos)
docker compose down -v       # remove também os volumes (reset completo)
```

## Comandos Make

| Comando | Descrição |
|---|---|
| `make setup` | Copia `.env.example` → `.env`, faz pull e build das imagens |
| `make up` / `make down` | Sobe / derruba o stack completo |
| `make logs` | Segue os logs de todos os serviços |
| `make migrate` | Aplica migrações Alembic |
| `make migration name=...` | Gera uma nova migração autogenerada |
| `make seed` | Popula usuários padrão de desenvolvimento |
| `make test` | Executa a suíte de testes (pytest) |
| `make lint` / `make format` | Ruff check / Ruff format |
| `make typecheck` | Mypy |
| `make security` | Roda o script de verificação de segurança |
| `make clean` | Derruba o stack e remove volumes |

## Endereços locais

| Serviço | Endereço | Credenciais padrão |
|---|---|---|
| Frontend | http://localhost:3000 | — |
| API | http://localhost:8000 | — |
| Swagger / OpenAPI | http://localhost:8000/docs | — |
| RabbitMQ Management | http://localhost:15672 | `factory` / `factory` |
| MinIO Console | http://localhost:9001 | `factory` / `local-development-password` |
| Grafana | http://localhost:3001 | `admin` / `admin` |
| Prometheus | http://localhost:9090 | — |
| Langfuse (perfil observability) | http://localhost:3002 | — |
| PostgreSQL | `localhost:5433` (mapeado; `5432` internamente) | `factory` / `factory` |
| Redis | `localhost:6379` | — |
| Ollama (host) | http://localhost:11434 | — |

> A porta do PostgreSQL é publicada como `5433` no host para evitar conflito com outras
> instâncias locais; a comunicação entre containers continua em `postgres:5432`.

**Credenciais padrão são apenas para uso local.** Troque-as antes de qualquer exposição além do
seu ambiente de desenvolvimento.

## Usuários padrão (seed)

O comando `make seed` (ou `python -m app.db.seed`) cria os seguintes usuários de desenvolvimento:

| Usuário | Senha | Papel |
|---|---|---|
| `admin` | `admin` | `ADMIN` |
| `manager` | `manager` | `FACTORY_MANAGER` |
| `approver` | `approver` | `APPROVER` |
| `developer` | `developer` | `DEVELOPER` |
| `auditor` | `auditor` | `AUDITOR` |
| `viewer` | `viewer` | `VIEWER` |

Senhas iguais ao usuário, válidas **apenas para desenvolvimento local**.

## Observabilidade

- **Métricas:** Prometheus + Grafana (dashboards provisionados em
  `infrastructure/grafana/provisioning`).
- **Logs:** Loki, agregando logs estruturados em JSON (`shared/logging`).
- **Tracing:** OpenTelemetry Collector, exportando para o backend configurado.
- **Observabilidade de LLM:** Langfuse (opcional, via `docker-compose.observability.yml`),
  rastreando prompts, tokens e latência de cada chamada aos modelos Ollama.

## Resiliência do orquestrador

- **Checkpoints persistentes:** o estado do grafo é salvo no PostgreSQL
  (`AsyncPostgresSaver`). Reiniciar o orquestrador não perde o progresso: a execução retoma do
  último nó concluído, em vez de refazer o pipeline.
- **Reconciliação automática:** na subida, execuções em `RUNNING`/`WAITING_HUMAN` sem atualização
  há mais de 180s são detectadas e retomadas — cobre o caso de o processo morrer no meio de uma
  etapa.
- **Retomada correta após revisão humana:** aprovar uma revisão por limite de ciclos retoma na
  etapa seguinte ao gate que escalou e zera os contadores de todos os gates.

> Ressalva: um nó parado aguardando decisão humana refaz o próprio nó ao retomar (a espera é um
> polling, não um estado suspenso). O trabalho já concluído das etapas anteriores é preservado.

## Documentação adicional

- [`docs/architecture/overview.md`](docs/architecture/overview.md) — visão geral da arquitetura
- [`docs/adrs/`](docs/adrs/) — Architecture Decision Records (LangGraph, Ollama, RabbitMQ,
  PostgreSQL, MinIO, workers por domínio, sandbox efêmero, configuração declarativa)
- [`docs/agents/README.md`](docs/agents/README.md) — detalhes do runtime de agentes
- [`docs/api/README.md`](docs/api/README.md) — documentação da API
- [`docs/operations/runbook.md`](docs/operations/runbook.md) — runbook operacional
- [`docs/security/README.md`](docs/security/README.md) — práticas e controles de segurança
- [`proposta_fabrica_software_multiagente_local.md`](proposta_fabrica_software_multiagente_local.md) —
  proposta original de arquitetura (v1.0)
