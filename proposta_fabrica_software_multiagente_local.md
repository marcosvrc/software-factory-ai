# Proposta de Arquitetura Local Multiagente para uma Fábrica de Software

**Versão:** 1.0  
**Status:** Proposta inicial para desenvolvimento  
**Execução:** Local com Docker Compose  
**Linguagem principal:** Python  
**Orquestração de agentes:** LangGraph  
**Modelo de linguagem local:** Ollama  
**Licença sugerida do projeto:** Apache-2.0 ou MIT  

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Objetivos](#2-objetivos)
3. [Princípios arquiteturais](#3-princípios-arquiteturais)
4. [Escopo da primeira versão](#4-escopo-da-primeira-versão)
5. [Arquitetura da solução](#5-arquitetura-da-solução)
6. [Stack tecnológica](#6-stack-tecnológica)
7. [Papéis da fábrica](#7-papéis-da-fábrica)
8. [Organização dos agentes](#8-organização-dos-agentes)
9. [Fluxo completo de trabalho](#9-fluxo-completo-de-trabalho)
10. [Máquina de estados](#10-máquina-de-estados)
11. [Contratos dos agentes](#11-contratos-dos-agentes)
12. [Modelo de dados](#12-modelo-de-dados)
13. [Mensageria](#13-mensageria)
14. [Memória e contexto](#14-memória-e-contexto)
15. [Ferramentas dos agentes](#15-ferramentas-dos-agentes)
16. [Execução segura de código](#16-execução-segura-de-código)
17. [Human-in-the-loop](#17-human-in-the-loop)
18. [Quality gates](#18-quality-gates)
19. [Observabilidade](#19-observabilidade)
20. [Segurança](#20-segurança)
21. [Estrutura do repositório](#21-estrutura-do-repositório)
22. [Docker Compose](#22-docker-compose)
23. [Configuração dos agentes](#23-configuração-dos-agentes)
24. [APIs iniciais](#24-apis-iniciais)
25. [Eventos internos](#25-eventos-internos)
26. [Estratégia de testes](#26-estratégia-de-testes)
27. [Definition of Ready e Definition of Done](#27-definition-of-ready-e-definition-of-done)
28. [Roadmap de implementação](#28-roadmap-de-implementação)
29. [Backlog inicial](#29-backlog-inicial)
30. [Comandos para iniciar](#30-comandos-para-iniciar)
31. [Critérios de sucesso](#31-critérios-de-sucesso)
32. [Evoluções futuras](#32-evoluções-futuras)
33. [Riscos e mitigações](#33-riscos-e-mitigações)
34. [Decisões arquiteturais iniciais](#34-decisões-arquiteturais-iniciais)
35. [Checklist para início do desenvolvimento](#35-checklist-para-início-do-desenvolvimento)

---

# 1. Visão geral

Este documento propõe uma arquitetura local para uma fábrica de software baseada em múltiplos agentes de inteligência artificial. Cada agente representa um papel especializado do ciclo de desenvolvimento de software, com responsabilidades, entradas, saídas, ferramentas, restrições e critérios de aprovação próprios.

A solução será executada inicialmente em uma máquina local por meio de Docker Compose. O objetivo é permitir que uma demanda percorra um fluxo controlado desde a descoberta do problema até a geração de código, testes, validação de segurança, documentação e preparação de release.

A arquitetura não será baseada em uma conversa livre entre agentes. O fluxo será controlado por um orquestrador, com:

- estados explícitos;
- tarefas persistidas;
- transições condicionais;
- filas por domínio;
- rastreabilidade das decisões;
- limites de repetição;
- aprovação humana;
- artefatos versionados;
- isolamento para execução de código.

---

# 2. Objetivos

## 2.1 Objetivo principal

Criar uma plataforma local e extensível que coordene agentes especializados para executar atividades de uma fábrica de software de forma rastreável, segura e parcialmente autônoma.

## 2.2 Objetivos específicos

- Representar os principais papéis de produto, engenharia, qualidade, segurança e operação.
- Automatizar a transformação de uma demanda em artefatos de software.
- Garantir separação entre criação, revisão e aprovação.
- Registrar todas as decisões relevantes.
- Permitir ciclos de correção controlados.
- Executar modelos de linguagem localmente.
- Integrar ferramentas reais de desenvolvimento.
- Possibilitar aprovação humana em etapas críticas.
- Fornecer métricas, logs e traces.
- Permitir evolução posterior para ambientes distribuídos.

## 2.3 Não objetivos da primeira versão

- Substituir integralmente equipes humanas.
- Realizar implantação automática em produção.
- Operar múltiplos clusters Kubernetes.
- Suportar centenas de execuções simultâneas.
- Tomar decisões jurídicas ou aceitar riscos críticos sem aprovação humana.
- Permitir acesso irrestrito dos agentes ao sistema operacional.
- Criar um agente independente para cada cargo desde o primeiro release.

---

# 3. Princípios arquiteturais

## 3.1 Orquestração explícita

O fluxo deve estar definido em código e configuração. Decisões estruturais não devem ficar escondidas apenas em prompts.

## 3.2 Responsabilidade única

Cada agente deve possuir uma responsabilidade principal claramente delimitada.

## 3.3 Fonte de verdade persistente

PostgreSQL será a fonte de verdade para estado, tarefas, decisões, aprovações e auditoria.

## 3.4 Artefatos como meio de colaboração

Os agentes colaboram principalmente por artefatos estruturados e versionados, não por histórico livre de conversa.

## 3.5 Separação entre produção e validação

O agente que produz um artefato não deve ser o único responsável por aprová-lo.

## 3.6 Menor privilégio

Cada worker recebe somente as ferramentas e permissões necessárias para executar sua função.

## 3.7 Execução determinística quando possível

Operações como validação de schema, lint, testes, análise estática e cálculo de métricas devem usar ferramentas determinísticas.

## 3.8 LLM como componente, não como autoridade final

O modelo propõe, interpreta e consolida. Ferramentas, regras e aprovações controlam a execução.

## 3.9 Human-in-the-loop

Mudanças de escopo, riscos críticos, release e ações destrutivas exigem aprovação humana.

## 3.10 Observabilidade desde o início

Cada execução deve produzir logs, métricas, traces, eventos e artefatos auditáveis.

---

# 4. Escopo da primeira versão

A primeira versão deverá permitir:

1. Criar um projeto.
2. Registrar uma demanda.
3. Executar descoberta e requisitos.
4. Gerar proposta de arquitetura.
5. Criar backlog técnico.
6. Gerar ou alterar código em um workspace isolado.
7. Revisar código com um agente diferente.
8. Executar lint e testes.
9. Realizar análise básica de segurança.
10. Produzir documentação.
11. Consolidar relatório final.
12. Solicitar aprovação humana.
13. Registrar toda a execução.

---

# 5. Arquitetura da solução

## 5.1 Visão lógica

```mermaid
flowchart TB
    U[Usuário] --> UI[Frontend Web]
    UI --> API[Factory API - FastAPI]
    API --> ORC[Orquestrador - LangGraph]
    ORC --> DB[(PostgreSQL)]
    ORC --> MQ[RabbitMQ]
    ORC --> OBJ[MinIO]

    MQ --> PW[Product Workers]
    MQ --> AW[Architecture Workers]
    MQ --> EW[Engineering Workers]
    MQ --> VW[Validation Workers]
    MQ --> OW[Operations Workers]

    PW --> LLM[Ollama]
    AW --> LLM
    EW --> LLM
    VW --> LLM
    OW --> LLM

    EW --> SB[Sandbox de execução]
    VW --> SB

    ORC --> LF[Langfuse]
    API --> OTEL[OpenTelemetry Collector]
    ORC --> OTEL
    PW --> OTEL
    AW --> OTEL
    EW --> OTEL
    VW --> OTEL
    OW --> OTEL

    OTEL --> PROM[Prometheus]
    OTEL --> LOKI[Loki]
    PROM --> GRAF[Grafana]
    LOKI --> GRAF
```

## 5.2 Camadas

### Camada de apresentação

- React ou Next.js.
- Acompanhamento de projetos.
- Visualização de estados.
- Aprovações humanas.
- Consulta a artefatos.
- Visualização de logs e resultados.

### Camada de API

- FastAPI.
- Autenticação local.
- Gerenciamento de projetos.
- Criação de demandas.
- Aprovações.
- Consulta a execuções.
- Download de artefatos.

### Camada de orquestração

- LangGraph.
- Máquina de estados.
- Seleção de agentes.
- Controle de retries.
- Controle de loops de correção.
- Checkpoints.
- Interrupções para aprovação.
- Consolidação de resultados.

### Camada de execução

Workers separados por domínio:

- product-workers;
- architecture-workers;
- engineering-workers;
- validation-workers;
- operations-workers.

### Camada de modelo

- Ollama executado preferencialmente no host.
- API acessível aos containers.
- Modelos diferentes por perfil de tarefa.
- Possibilidade futura de vLLM em Linux com GPU.

### Camada de dados

- PostgreSQL para estado e auditoria.
- Redis para cache, locks e dados temporários.
- RabbitMQ para tarefas.
- MinIO para artefatos.
- Git para versionamento do workspace.

### Camada de observabilidade

- Langfuse para traces de LLM.
- OpenTelemetry para telemetria.
- Prometheus para métricas.
- Grafana para dashboards.
- Loki para logs.

---

# 6. Stack tecnológica

| Componente | Tecnologia inicial | Responsabilidade |
|---|---|---|
| Linguagem | Python 3.12+ | Agentes, API e workers |
| API | FastAPI | Interface HTTP |
| Orquestração | LangGraph | Fluxos, estados e interrupções |
| Modelos locais | Ollama | Inferência local |
| Banco principal | PostgreSQL | Fonte de verdade |
| Cache e locks | Redis | Estado temporário |
| Mensageria | RabbitMQ | Filas e distribuição |
| Object storage | MinIO | Artefatos |
| ORM | SQLAlchemy 2 | Persistência |
| Migrações | Alembic | Evolução do banco |
| Validação | Pydantic 2 | Contratos e schemas |
| Tarefas | Celery, Dramatiq ou consumidor próprio | Consumo de filas |
| Frontend | React ou Next.js | Interface do usuário |
| Tracing LLM | Langfuse | Prompts, respostas e avaliações |
| Telemetria | OpenTelemetry | Traces e métricas |
| Métricas | Prometheus | Coleta de métricas |
| Dashboards | Grafana | Visualização |
| Logs | Loki | Agregação de logs |
| Testes | Pytest | Testes automatizados |
| Qualidade Python | Ruff, Mypy, Bandit | Lint, tipos e segurança |
| Segurança de dependências | Trivy, pip-audit | Vulnerabilidades |
| Segredos | Gitleaks | Detecção de segredos |
| Containers | Docker Compose | Execução local |
| Repositório local | Git + Gitea opcional | Versionamento |

---

# 7. Papéis da fábrica

Os papéis serão representados por agentes lógicos. Nem todos precisam ser processos independentes.

## 7.1 Coordenação e governança

### Orquestrador

- recebe demandas;
- cria o plano;
- escolhe agentes;
- controla estados;
- verifica quality gates;
- limita ciclos;
- solicita aprovações;
- consolida resultados.

### Engineering Manager

- avalia capacidade dos workers;
- prioriza tarefas técnicas;
- acompanha métricas de engenharia;
- identifica gargalos;
- recomenda redistribuição.

### Flow Manager ou Scrum Master

- acompanha fluxo;
- identifica bloqueios;
- controla trabalho em andamento;
- acompanha dependências;
- gera retrospectiva.

### Gestor de Portfólio

- prioriza projetos;
- identifica conflitos;
- acompanha benefícios e custos;
- consolida indicadores.

### Gestor de Riscos

- mantém registro de riscos;
- classifica probabilidade e impacto;
- acompanha mitigações;
- escala riscos críticos.

---

## 7.2 Produto e descoberta

### Product Manager

- define visão;
- identifica valor esperado;
- define métricas;
- mantém roadmap.

### Product Owner

- prioriza backlog;
- esclarece objetivos;
- valida aceite de negócio;
- representa o usuário.

### Analista de Negócios

- identifica regras;
- modela processos;
- mapeia atores;
- documenta exceções.

### Analista de Requisitos

- cria histórias;
- define critérios de aceite;
- registra requisitos funcionais e não funcionais;
- verifica testabilidade.

### UX Researcher

- cria hipóteses sobre usuários;
- define pesquisas;
- sintetiza necessidades;
- registra riscos de usabilidade.

### UX/UI Designer

- cria fluxos;
- produz wireframes;
- define componentes;
- verifica acessibilidade.

---

## 7.3 Arquitetura

### Arquiteto de Solução

- define visão técnica;
- seleciona padrões;
- cria diagramas;
- avalia atributos de qualidade;
- registra ADRs.

### Arquiteto de Software

- define módulos;
- interfaces internas;
- padrões de implementação;
- regras de dependência.

### Arquiteto de Dados

- define modelos;
- persistência;
- retenção;
- integridade;
- migração.

### Arquiteto de Integração

- define APIs;
- eventos;
- contratos;
- versionamento;
- idempotência.

### Arquiteto de Segurança

- define trust boundaries;
- cria threat model;
- define controles;
- avalia riscos arquiteturais.

### Governança de Arquitetura

- verifica conformidade;
- mantém padrões;
- registra exceções;
- identifica dívida arquitetural.

### Tech Lead

- transforma arquitetura em tarefas;
- orienta implementação;
- resolve decisões técnicas locais;
- valida aderência.

---

## 7.4 Desenvolvimento

### Desenvolvedor Backend

- implementa serviços;
- regras de negócio;
- APIs;
- persistência;
- integrações;
- testes.

### Desenvolvedor Frontend

- implementa interface;
- acessibilidade;
- integração com APIs;
- testes de componentes.

### Desenvolvedor Mobile

- implementa aplicações móveis quando aplicável;
- gerencia permissões;
- armazenamento local;
- notificações.

### Engenheiro de Integração

- implementa conectores;
- contratos;
- consumidores;
- produtores de eventos.

### Engenheiro de Dados

- implementa pipelines;
- transformações;
- validação de qualidade;
- linhagem.

### Revisor de Código

- verifica legibilidade;
- aderência à arquitetura;
- testes;
- segurança básica;
- manutenibilidade.

### Agente de Refatoração

- identifica duplicação;
- complexidade;
- acoplamento;
- propõe melhorias sem alterar comportamento.

---

## 7.5 Qualidade

### QA Lead

- define estratégia de qualidade;
- estabelece cobertura;
- consolida parecer.

### QA Funcional

- deriva cenários;
- executa validações;
- registra defeitos;
- verifica aceite.

### Automação de Testes

- cria testes de API;
- integração;
- interface;
- regressão.

### Testes de Performance

- cria cenários de carga;
- mede latência;
- identifica gargalos.

### Acessibilidade

- verifica WCAG;
- navegação por teclado;
- semântica;
- contraste.

### Dados de Teste

- cria massa sintética;
- mascara dados;
- garante cobertura.

### Avaliação de IA

Quando o projeto gerado utilizar IA:

- cria datasets de avaliação;
- mede qualidade;
- verifica regressão;
- avalia alucinação e segurança.

---

## 7.6 Segurança, privacidade e conformidade

### AppSec

- executa SAST;
- revisa autenticação;
- identifica vulnerabilidades;
- acompanha correções.

### DevSecOps

- integra scanners ao pipeline;
- define gates;
- verifica imagens e dependências.

### Privacidade

- identifica dados pessoais;
- avalia minimização;
- retenção;
- consentimento;
- descarte.

### Conformidade

- verifica políticas;
- requisitos regulatórios;
- evidências;
- rastreabilidade.

### Jurídico

- avalia termos;
- licenças;
- contratos;
- propriedade intelectual.

### Open Source e Licenciamento

- cria SBOM;
- verifica licenças;
- identifica incompatibilidades;
- monitora componentes abandonados.

### Segurança de IA

- avalia prompt injection;
- vazamento de dados;
- abuso de ferramentas;
- riscos de modelos.

---

## 7.7 Plataforma e operação

### DevOps

- cria pipeline;
- automatiza build;
- testes;
- empacotamento;
- release.

### Engenheiro de Plataforma

- cria templates;
- ambientes;
- catálogos;
- experiência do desenvolvedor.

### Infraestrutura

- define recursos;
- redes;
- volumes;
- infraestrutura como código.

### Gestão de Configuração

- controla versões;
- parâmetros;
- feature flags;
- compatibilidade.

### DBA ou Database Reliability Engineer

- otimiza consultas;
- índices;
- backup;
- restauração;
- disponibilidade.

### SRE

- define SLI e SLO;
- dashboards;
- alertas;
- runbooks;
- resiliência.

### FinOps

- estima consumo;
- custo de inferência;
- custo por execução;
- otimização.

### Gestão de Ambientes

- verifica disponibilidade;
- consistência;
- dependências;
- dados de teste.

---

## 7.8 Entrega e sustentação

### Release Manager

- verifica aprovações;
- consolida release notes;
- valida rollback;
- coordena release.

### Change Manager

- classifica mudanças;
- avalia impacto;
- verifica plano;
- registra aprovação.

### Incident Manager

- coordena incidentes;
- classifica severidade;
- mantém timeline;
- comunica status.

### Problem Manager

- investiga recorrência;
- conduz causa raiz;
- acompanha ações preventivas.

### Suporte Técnico

- classifica chamados;
- consulta base de conhecimento;
- resolve problemas conhecidos;
- escala para engenharia.

### Documentação Técnica

- mantém README;
- guias;
- diagramas;
- APIs;
- runbooks.

### Developer Experience

- simplifica setup;
- reduz tempo de build;
- cria templates;
- melhora documentação interna.

---

# 8. Organização dos agentes

## 8.1 Agentes lógicos

Todos os papéis anteriores existirão como configurações lógicas.

## 8.2 Workers físicos iniciais

Para evitar dezenas de containers, os agentes serão agrupados por domínio:

```text
product-worker
├── product-manager
├── product-owner
├── business-analyst
├── requirements-analyst
├── ux-researcher
└── ux-ui-designer

architecture-worker
├── solution-architect
├── software-architect
├── data-architect
├── integration-architect
├── security-architect
├── architecture-governance
└── tech-lead

engineering-worker
├── backend-developer
├── frontend-developer
├── mobile-developer
├── integration-engineer
├── data-engineer
├── code-reviewer
└── refactoring-agent

validation-worker
├── qa-lead
├── functional-qa
├── test-automation
├── performance-test
├── accessibility
├── test-data
└── ai-evaluator

security-worker
├── appsec
├── devsecops
├── privacy
├── compliance
├── legal
├── open-source
└── ai-security

operations-worker
├── devops
├── platform-engineer
├── infrastructure
├── configuration-manager
├── dba
├── sre
├── finops
└── environment-manager

delivery-worker
├── release-manager
├── change-manager
├── incident-manager
├── problem-manager
├── support
├── documentation
└── developer-experience

governance-worker
├── engineering-manager
├── flow-manager
├── portfolio-manager
└── risk-manager
```

## 8.3 Critério de separação futura

Um agente deverá virar container próprio quando:

- precisar escalar de forma independente;
- utilizar dependências incompatíveis;
- exigir permissões diferenciadas;
- consumir muitos recursos;
- precisar de isolamento adicional;
- possuir fila e SLA próprios.

---

# 9. Fluxo completo de trabalho

```mermaid
flowchart TD
    A[Demanda criada] --> B[Triagem do orquestrador]
    B --> C[Produto e descoberta]
    C --> D[Requisitos]
    D --> E{Aprovação de escopo}
    E -- Reprovado --> C
    E -- Aprovado --> F[Arquitetura]
    F --> G{Architecture gate}
    G -- Ajustes --> F
    G -- Aprovado --> H[Planejamento técnico]
    H --> I[Desenvolvimento]
    I --> J[Code review]
    J -- Reprovado --> I
    J -- Aprovado --> K[Testes automatizados]
    K -- Falha --> I
    K -- Sucesso --> L[QA funcional]
    L -- Reprovado --> I
    L -- Aprovado --> M[Segurança e conformidade]
    M -- Reprovado --> I
    M -- Aprovado --> N[Validação operacional]
    N -- Reprovado --> H
    N -- Aprovado --> O[Documentação e release]
    O --> P{Aprovação humana}
    P -- Reprovado --> H
    P -- Aprovado --> Q[Entrega concluída]
```

## 9.1 Limites de iteração

- Máximo de três ciclos automáticos por gate.
- Após o terceiro ciclo, o item muda para `HUMAN_REVIEW_REQUIRED`.
- O orquestrador não pode criar loops ilimitados.
- Cada correção deve referenciar os achados que motivaram o retorno.

## 9.2 Paralelismo

Podem executar em paralelo:

- UX e requisitos não funcionais;
- arquitetura de dados e integração;
- documentação técnica e testes;
- AppSec e análise de licenças;
- observabilidade e infraestrutura.

Não devem executar em paralelo quando houver dependência direta não resolvida.

---

# 10. Máquina de estados

## 10.1 Estados do projeto

```text
DRAFT
PLANNING
ACTIVE
WAITING_APPROVAL
BLOCKED
COMPLETED
CANCELLED
ARCHIVED
```

## 10.2 Estados de uma execução

```text
CREATED
QUEUED
RUNNING
WAITING_TOOL
WAITING_AGENT
WAITING_HUMAN
RETRYING
PARTIALLY_COMPLETED
COMPLETED
FAILED_RETRYABLE
FAILED_FINAL
CANCELLED
```

## 10.3 Estados de uma tarefa

```text
BACKLOG
READY
IN_PROGRESS
IN_REVIEW
CHANGES_REQUESTED
IN_TEST
SECURITY_REVIEW
OPERATIONAL_REVIEW
READY_FOR_RELEASE
DONE
BLOCKED
FAILED
CANCELLED
```

## 10.4 Regras

- Somente o orquestrador altera o estado global.
- Workers alteram apenas o status de sua execução.
- Toda transição gera um evento de auditoria.
- Transições inválidas devem retornar erro.
- Uma tarefa concluída não pode ser alterada sem nova versão.
- Cancelamento não apaga histórico ou artefatos.

---

# 11. Contratos dos agentes

## 11.1 Contrato padrão

```yaml
id: architecture.solution
name: Arquiteto de Solução
version: 1.0.0
domain: architecture

objective: >
  Produzir uma arquitetura coerente com os requisitos funcionais,
  requisitos não funcionais e restrições do projeto.

inputs:
  required:
    - product_vision
    - functional_requirements
    - non_functional_requirements
    - constraints
  optional:
    - existing_architecture
    - technology_catalog
    - risk_register

outputs:
  schema: schemas/architecture-proposal.schema.json
  artifacts:
    - architecture/solution-architecture.md
    - architecture/context.mmd
    - architecture/container.mmd
    - architecture/adrs/

tools:
  allowed:
    - repository.read
    - artifact.read
    - artifact.write
    - diagram.generate
    - standards.search
  denied:
    - shell.unrestricted
    - production.deploy
    - secrets.read

model:
  provider: ollama
  primary: qwen2.5-coder
  fallback: llama3.1
  temperature: 0.2
  max_context_tokens: 32000

quality_gates:
  - requirements_traceability
  - security_considerations
  - data_design
  - failure_modes
  - observability_design
  - deployment_design

retry:
  max_attempts: 2
  on_failure: human_review

escalation:
  - tech-lead
  - security-architect
  - human-architect
```

## 11.2 Elementos obrigatórios

Todo agente deve possuir:

- identificador;
- nome;
- versão;
- domínio;
- objetivo;
- entradas obrigatórias;
- entradas opcionais;
- schema de saída;
- lista de artefatos;
- ferramentas permitidas;
- ferramentas proibidas;
- modelo;
- parâmetros;
- gates;
- política de retry;
- escalonamento.

## 11.3 Saídas estruturadas

As respostas devem utilizar Pydantic e JSON Schema. Texto livre será permitido apenas dentro de campos definidos.

Exemplo:

```python
from pydantic import BaseModel, Field
from typing import Literal


class Finding(BaseModel):
    id: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    category: str
    description: str
    evidence: list[str]
    recommendation: str


class AgentResult(BaseModel):
    agent_id: str
    execution_id: str
    status: Literal["approved", "changes_requested", "blocked", "failed"]
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    next_recommended_agents: list[str] = Field(default_factory=list)
```

---

# 12. Modelo de dados

## 12.1 Entidades principais

### PROJECT

- id;
- name;
- description;
- status;
- repository_url;
- workspace_path;
- created_at;
- updated_at.

### DEMAND

- id;
- project_id;
- title;
- description;
- priority;
- requester;
- business_value;
- status.

### WORKFLOW_RUN

- id;
- project_id;
- demand_id;
- graph_version;
- status;
- current_node;
- started_at;
- finished_at;
- correlation_id.

### TASK

- id;
- workflow_run_id;
- parent_task_id;
- type;
- title;
- description;
- assigned_agent_id;
- status;
- attempt;
- max_attempts;
- priority.

### AGENT_DEFINITION

- id;
- name;
- version;
- domain;
- configuration;
- enabled.

### AGENT_EXECUTION

- id;
- task_id;
- agent_id;
- model;
- prompt_version;
- status;
- input_reference;
- output_reference;
- token_usage;
- duration_ms;
- error_code.

### ARTIFACT

- id;
- project_id;
- workflow_run_id;
- task_id;
- type;
- name;
- storage_key;
- checksum;
- version;
- created_by;
- created_at.

### FINDING

- id;
- task_id;
- agent_execution_id;
- category;
- severity;
- description;
- evidence;
- recommendation;
- status.

### DECISION

- id;
- workflow_run_id;
- task_id;
- decision_type;
- rationale;
- options_considered;
- selected_option;
- decided_by;
- created_at.

### APPROVAL

- id;
- workflow_run_id;
- task_id;
- approval_type;
- status;
- requested_from;
- decided_by;
- rationale;
- requested_at;
- decided_at.

### AUDIT_EVENT

- id;
- correlation_id;
- actor_type;
- actor_id;
- event_type;
- entity_type;
- entity_id;
- before_state;
- after_state;
- metadata;
- created_at.

### TOOL_EXECUTION

- id;
- agent_execution_id;
- tool_name;
- input_hash;
- output_reference;
- status;
- started_at;
- finished_at.

### RISK

- id;
- project_id;
- category;
- description;
- probability;
- impact;
- score;
- owner;
- mitigation;
- status.

## 12.2 Relacionamentos

```mermaid
erDiagram
    PROJECT ||--o{ DEMAND : contains
    PROJECT ||--o{ WORKFLOW_RUN : executes
    PROJECT ||--o{ ARTIFACT : owns
    PROJECT ||--o{ RISK : has

    DEMAND ||--o{ WORKFLOW_RUN : triggers
    WORKFLOW_RUN ||--o{ TASK : contains
    WORKFLOW_RUN ||--o{ DECISION : records
    WORKFLOW_RUN ||--o{ APPROVAL : requires
    WORKFLOW_RUN ||--o{ AUDIT_EVENT : produces

    TASK ||--o{ AGENT_EXECUTION : executes
    TASK ||--o{ FINDING : produces
    TASK ||--o{ ARTIFACT : creates

    AGENT_DEFINITION ||--o{ AGENT_EXECUTION : performs
    AGENT_EXECUTION ||--o{ TOOL_EXECUTION : invokes
    AGENT_EXECUTION ||--o{ FINDING : reports
```

---

# 13. Mensageria

## 13.1 RabbitMQ

RabbitMQ será utilizado como broker principal.

## 13.2 Exchanges

```text
factory.commands
factory.events
factory.dead-letter
```

## 13.3 Filas

```text
factory.product
factory.architecture
factory.engineering
factory.validation
factory.security
factory.operations
factory.delivery
factory.governance
factory.dead-letter
```

## 13.4 Estrutura de mensagem

```json
{
  "message_id": "uuid",
  "correlation_id": "uuid",
  "causation_id": "uuid",
  "workflow_run_id": "uuid",
  "task_id": "uuid",
  "agent_id": "architecture.solution",
  "command": "execute_agent",
  "priority": 5,
  "attempt": 1,
  "created_at": "2026-07-30T22:00:00-03:00",
  "payload_reference": "minio://factory/inputs/task.json"
}
```

## 13.5 Regras

- Confirmação manual após persistência do resultado.
- Retry com backoff exponencial.
- Dead-letter após limite de tentativas.
- Idempotência baseada em `message_id`.
- Toda mensagem deve conter `correlation_id`.
- Payloads grandes devem ficar no MinIO.

---

# 14. Memória e contexto

## 14.1 Tipos de memória

### Memória de execução

- estado atual;
- tarefas;
- resultados recentes;
- decisões do workflow.

Armazenamento: PostgreSQL.

### Memória de projeto

- visão;
- requisitos;
- ADRs;
- convenções;
- glossário;
- arquitetura;
- riscos.

Armazenamento: Git, PostgreSQL e MinIO.

### Memória semântica

- documentação indexada;
- padrões;
- conhecimento reutilizável;
- decisões anteriores.

Armazenamento futuro: PostgreSQL com pgvector.

### Memória temporária

- cache;
- locks;
- rate limits;
- contexto de curta duração.

Armazenamento: Redis.

## 14.2 Context builder

Antes de chamar um agente, o orquestrador cria um pacote de contexto contendo apenas:

- objetivo da tarefa;
- entradas obrigatórias;
- artefatos relevantes;
- decisões aplicáveis;
- findings pendentes;
- restrições;
- ferramentas permitidas;
- schema da resposta.

## 14.3 Política de contexto

- Não enviar o histórico completo do projeto.
- Resumir artefatos longos.
- Registrar quais fontes foram usadas.
- Limitar tamanho por agente.
- Não incluir segredos.
- Marcar conteúdo não confiável.
- Separar instruções de dados externos.

---

# 15. Ferramentas dos agentes

## 15.1 Ferramentas iniciais

```text
repository.read
repository.diff
repository.create_branch
repository.commit

artifact.read
artifact.write
artifact.list

code.search
code.patch
code.format

test.run_unit
test.run_integration
test.run_e2e

quality.run_lint
quality.run_type_check
quality.run_complexity

security.run_sast
security.scan_dependencies
security.scan_secrets
security.scan_container

container.build
container.run_sandbox

database.inspect_schema
database.validate_migration

documentation.generate
diagram.generate

workflow.request_approval
workflow.report_finding
workflow.complete_task
```

## 15.2 Abstração

As ferramentas devem ser expostas por interfaces internas ou por MCP futuramente.

```python
from typing import Protocol, Any


class Tool(Protocol):
    name: str

    async def execute(
        self,
        *,
        execution_id: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        ...
```

## 15.3 Política de autorização

Cada chamada deve validar:

- agente solicitante;
- tarefa;
- escopo;
- workspace;
- ferramenta;
- argumentos;
- limite de tempo;
- limite de recursos.

---

# 16. Execução segura de código

## 16.1 Princípio

Código gerado nunca será executado diretamente no container do orquestrador.

## 16.2 Sandbox

Cada execução utilizará um container efêmero com:

- usuário não root;
- filesystem somente leitura, exceto workspace;
- rede desabilitada por padrão;
- CPU limitada;
- memória limitada;
- timeout;
- sem acesso ao socket Docker;
- sem acesso a segredos;
- volume dedicado;
- imagem previamente aprovada.

## 16.3 Fluxo

```text
Agente gera patch
      ↓
Patch validado
      ↓
Workspace isolado
      ↓
Container efêmero
      ↓
Lint e testes
      ↓
Coleta de evidências
      ↓
Container removido
```

## 16.4 Proibições

- `--privileged`;
- montagem de `/`;
- montagem de `/var/run/docker.sock`;
- execução como root;
- acesso livre à internet;
- leitura de diretórios do host;
- execução de scripts sem timeout.

---

# 17. Human-in-the-loop

## 17.1 Aprovações obrigatórias

- aprovação do escopo;
- aceitação de risco crítico;
- alteração de arquitetura de alto impacto;
- mudança destrutiva no banco;
- acesso a fontes externas;
- release;
- implantação;
- rollback;
- exceção de segurança;
- uso de licença incompatível.

## 17.2 Estados de aprovação

```text
REQUESTED
APPROVED
REJECTED
EXPIRED
CANCELLED
```

## 17.3 Conteúdo de uma solicitação

- decisão solicitada;
- resumo;
- impactos;
- riscos;
- alternativas;
- recomendação;
- artefatos associados;
- prazo;
- ações possíveis.

---

# 18. Quality gates

## Gate 1 — Descoberta

- problema definido;
- objetivo definido;
- usuário identificado;
- valor esperado;
- métricas propostas.

## Gate 2 — Requisitos

- histórias testáveis;
- critérios de aceite;
- regras de negócio;
- requisitos não funcionais;
- exceções;
- rastreabilidade.

## Gate 3 — Arquitetura

- componentes definidos;
- dados definidos;
- integrações definidas;
- segurança considerada;
- observabilidade considerada;
- riscos registrados;
- ADRs criados.

## Gate 4 — Desenvolvimento

- build concluído;
- lint aprovado;
- tipos aprovados;
- testes unitários;
- cobertura mínima;
- ausência de segredos.

## Gate 5 — Code review

- aderência à arquitetura;
- legibilidade;
- tratamento de erros;
- testes suficientes;
- sem findings críticos.

## Gate 6 — QA

- critérios de aceite cobertos;
- regressão aprovada;
- defeitos críticos inexistentes;
- evidências registradas.

## Gate 7 — Segurança

- SAST aprovado;
- dependências avaliadas;
- imagem analisada;
- licenças avaliadas;
- nenhum risco crítico aberto.

## Gate 8 — Operação

- health checks;
- logs;
- métricas;
- alertas;
- backup;
- rollback;
- runbook.

## Gate 9 — Release

- todos os gates aprovados;
- release notes;
- versão definida;
- aprovação humana;
- artefatos íntegros.

---

# 19. Observabilidade

## 19.1 Logs

Formato JSON:

```json
{
  "timestamp": "2026-07-30T22:00:00-03:00",
  "level": "INFO",
  "service": "architecture-worker",
  "correlation_id": "uuid",
  "workflow_run_id": "uuid",
  "task_id": "uuid",
  "agent_id": "architecture.solution",
  "event": "agent_execution_completed",
  "duration_ms": 8250
}
```

## 19.2 Métricas

### Workflow

- workflows iniciados;
- workflows concluídos;
- workflows falhos;
- duração por etapa;
- tempo em aprovação;
- quantidade de retries;
- taxa de bloqueio.

### Agentes

- execuções por agente;
- duração;
- sucesso;
- falha;
- findings;
- chamadas de ferramentas;
- tokens ou unidades equivalentes;
- tamanho de contexto.

### Engenharia

- testes executados;
- cobertura;
- defeitos;
- complexidade;
- vulnerabilidades;
- tempo de correção.

### Infraestrutura

- CPU;
- memória;
- disco;
- filas;
- latência do modelo;
- disponibilidade dos serviços.

## 19.3 Traces

Um trace deve conectar:

```text
HTTP Request
  → Workflow Run
    → Task
      → Agent Execution
        → Model Call
        → Tool Execution
        → Artifact
```

---

# 20. Segurança

## 20.1 Autenticação inicial

- Usuários locais armazenados no PostgreSQL.
- Senhas com Argon2id.
- JWT de curta duração.
- Refresh token rotativo.

## 20.2 Autorização

Papéis iniciais:

```text
ADMIN
FACTORY_MANAGER
APPROVER
DEVELOPER
AUDITOR
VIEWER
```

## 20.3 Segredos

- Arquivo `.env` somente em desenvolvimento.
- Nunca versionar segredos.
- Usar Docker secrets quando possível.
- Preparar abstração para Vault no futuro.

## 20.4 Segurança dos prompts

- Separar instruções e conteúdo.
- Marcar conteúdo externo como não confiável.
- Validar chamadas de ferramentas.
- Não permitir que texto de artefato altere políticas.
- Exigir saída estruturada.
- Limitar autonomia.
- Registrar decisões.

## 20.5 Auditoria

Eventos append-only para:

- login;
- criação de projeto;
- mudança de estado;
- execução de agente;
- chamada de ferramenta;
- aprovação;
- alteração de configuração;
- geração de artefato;
- falha;
- cancelamento.

---

# 21. Estrutura do repositório

```text
software-factory/
├── README.md
├── Makefile
├── pyproject.toml
├── docker-compose.yml
├── docker-compose.observability.yml
├── .env.example
├── .gitignore
├── docs/
│   ├── architecture/
│   ├── adrs/
│   ├── agents/
│   ├── api/
│   ├── operations/
│   └── security/
├── frontend/
│   ├── src/
│   ├── tests/
│   └── Dockerfile
├── backend/
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── migrations/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── auth/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── events/
│   │   ├── messaging/
│   │   ├── observability/
│   │   └── security/
│   └── tests/
├── orchestrator/
│   ├── Dockerfile
│   ├── graphs/
│   │   ├── software_delivery.py
│   │   ├── incident_response.py
│   │   └── architecture_review.py
│   ├── nodes/
│   ├── routing/
│   ├── state/
│   ├── checkpoints/
│   └── tests/
├── agents/
│   ├── definitions/
│   │   ├── product/
│   │   ├── architecture/
│   │   ├── engineering/
│   │   ├── validation/
│   │   ├── security/
│   │   ├── operations/
│   │   ├── delivery/
│   │   └── governance/
│   ├── prompts/
│   ├── schemas/
│   ├── runtime/
│   └── registry.py
├── workers/
│   ├── product/
│   ├── architecture/
│   ├── engineering/
│   ├── validation/
│   ├── security/
│   ├── operations/
│   ├── delivery/
│   └── governance/
├── tools/
│   ├── repository/
│   ├── artifacts/
│   ├── code/
│   ├── testing/
│   ├── security/
│   ├── containers/
│   ├── database/
│   └── workflow/
├── sandbox/
│   ├── images/
│   ├── policies/
│   └── runner/
├── infrastructure/
│   ├── docker/
│   ├── prometheus/
│   ├── grafana/
│   ├── loki/
│   ├── otel/
│   ├── rabbitmq/
│   ├── minio/
│   └── scripts/
├── shared/
│   ├── contracts/
│   ├── exceptions/
│   ├── logging/
│   └── utils/
└── tests/
    ├── integration/
    ├── e2e/
    ├── security/
    └── performance/
```

---

# 22. Docker Compose

A configuração abaixo é um ponto de partida. Fixe versões específicas antes de usar fora do ambiente local.

```yaml
services:
  frontend:
    build:
      context: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      api:
        condition: service_healthy
    networks:
      - factory-network

  api:
    build:
      context: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+asyncpg://factory:factory@postgres:5432/factory
      REDIS_URL: redis://redis:6379/0
      RABBITMQ_URL: amqp://factory:factory@rabbitmq:5672/
      MINIO_ENDPOINT: minio:9000
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
      minio:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 10
    networks:
      - factory-network

  orchestrator:
    build:
      context: .
      dockerfile: orchestrator/Dockerfile
    command: python -m orchestrator.main
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+asyncpg://factory:factory@postgres:5432/factory
      REDIS_URL: redis://redis:6379/0
      RABBITMQ_URL: amqp://factory:factory@rabbitmq:5672/
      MINIO_ENDPOINT: minio:9000
      OLLAMA_BASE_URL: http://host.docker.internal:11434
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    networks:
      - factory-network

  product-worker:
    build:
      context: .
      dockerfile: workers/product/Dockerfile
    command: python -m workers.product.main
    env_file: [.env]
    environment:
      WORKER_DOMAIN: product
      RABBITMQ_URL: amqp://factory:factory@rabbitmq:5672/
      DATABASE_URL: postgresql+asyncpg://factory:factory@postgres:5432/factory
      OLLAMA_BASE_URL: http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      rabbitmq:
        condition: service_healthy
    networks:
      - factory-network

  architecture-worker:
    build:
      context: .
      dockerfile: workers/architecture/Dockerfile
    command: python -m workers.architecture.main
    env_file: [.env]
    environment:
      WORKER_DOMAIN: architecture
      RABBITMQ_URL: amqp://factory:factory@rabbitmq:5672/
      DATABASE_URL: postgresql+asyncpg://factory:factory@postgres:5432/factory
      OLLAMA_BASE_URL: http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      rabbitmq:
        condition: service_healthy
    networks:
      - factory-network

  engineering-worker:
    build:
      context: .
      dockerfile: workers/engineering/Dockerfile
    command: python -m workers.engineering.main
    env_file: [.env]
    environment:
      WORKER_DOMAIN: engineering
      RABBITMQ_URL: amqp://factory:factory@rabbitmq:5672/
      DATABASE_URL: postgresql+asyncpg://factory:factory@postgres:5432/factory
      OLLAMA_BASE_URL: http://host.docker.internal:11434
      SANDBOX_ENABLED: "true"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - workspaces:/workspaces
      - artifacts:/artifacts
    depends_on:
      rabbitmq:
        condition: service_healthy
    networks:
      - factory-network

  validation-worker:
    build:
      context: .
      dockerfile: workers/validation/Dockerfile
    command: python -m workers.validation.main
    env_file: [.env]
    environment:
      WORKER_DOMAIN: validation
      RABBITMQ_URL: amqp://factory:factory@rabbitmq:5672/
      DATABASE_URL: postgresql+asyncpg://factory:factory@postgres:5432/factory
      OLLAMA_BASE_URL: http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - workspaces:/workspaces:ro
      - artifacts:/artifacts
    depends_on:
      rabbitmq:
        condition: service_healthy
    networks:
      - factory-network

  security-worker:
    build:
      context: .
      dockerfile: workers/security/Dockerfile
    command: python -m workers.security.main
    env_file: [.env]
    environment:
      WORKER_DOMAIN: security
      RABBITMQ_URL: amqp://factory:factory@rabbitmq:5672/
      DATABASE_URL: postgresql+asyncpg://factory:factory@postgres:5432/factory
      OLLAMA_BASE_URL: http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - workspaces:/workspaces:ro
      - artifacts:/artifacts
    depends_on:
      rabbitmq:
        condition: service_healthy
    networks:
      - factory-network

  operations-worker:
    build:
      context: .
      dockerfile: workers/operations/Dockerfile
    command: python -m workers.operations.main
    env_file: [.env]
    environment:
      WORKER_DOMAIN: operations
      RABBITMQ_URL: amqp://factory:factory@rabbitmq:5672/
      DATABASE_URL: postgresql+asyncpg://factory:factory@postgres:5432/factory
      OLLAMA_BASE_URL: http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - workspaces:/workspaces:ro
      - artifacts:/artifacts
    depends_on:
      rabbitmq:
        condition: service_healthy
    networks:
      - factory-network

  delivery-worker:
    build:
      context: .
      dockerfile: workers/delivery/Dockerfile
    command: python -m workers.delivery.main
    env_file: [.env]
    environment:
      WORKER_DOMAIN: delivery
      RABBITMQ_URL: amqp://factory:factory@rabbitmq:5672/
      DATABASE_URL: postgresql+asyncpg://factory:factory@postgres:5432/factory
      OLLAMA_BASE_URL: http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - workspaces:/workspaces:ro
      - artifacts:/artifacts
    depends_on:
      rabbitmq:
        condition: service_healthy
    networks:
      - factory-network

  governance-worker:
    build:
      context: .
      dockerfile: workers/governance/Dockerfile
    command: python -m workers.governance.main
    env_file: [.env]
    environment:
      WORKER_DOMAIN: governance
      RABBITMQ_URL: amqp://factory:factory@rabbitmq:5672/
      DATABASE_URL: postgresql+asyncpg://factory:factory@postgres:5432/factory
      OLLAMA_BASE_URL: http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      rabbitmq:
        condition: service_healthy
    networks:
      - factory-network

  postgres:
    image: postgres:17
    environment:
      POSTGRES_DB: factory
      POSTGRES_USER: factory
      POSTGRES_PASSWORD: factory
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U factory -d factory"]
      interval: 5s
      timeout: 5s
      retries: 20
    networks:
      - factory-network

  redis:
    image: redis:8
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 20
    networks:
      - factory-network

  rabbitmq:
    image: rabbitmq:4-management
    environment:
      RABBITMQ_DEFAULT_USER: factory
      RABBITMQ_DEFAULT_PASS: factory
    volumes:
      - rabbitmq-data:/var/lib/rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "check_running"]
      interval: 10s
      timeout: 5s
      retries: 20
    networks:
      - factory-network

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: factory
      MINIO_ROOT_PASSWORD: local-development-password
    volumes:
      - minio-data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    networks:
      - factory-network

  otel-collector:
    image: otel/opentelemetry-collector-contrib
    command: ["--config=/etc/otelcol/config.yaml"]
    volumes:
      - ./infrastructure/otel/config.yaml:/etc/otelcol/config.yaml:ro
    ports:
      - "4317:4317"
      - "4318:4318"
    networks:
      - factory-network

  prometheus:
    image: prom/prometheus
    volumes:
      - ./infrastructure/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - factory-network

  loki:
    image: grafana/loki
    command: -config.file=/etc/loki/local-config.yaml
    volumes:
      - loki-data:/loki
    ports:
      - "3100:3100"
    networks:
      - factory-network

  grafana:
    image: grafana/grafana
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./infrastructure/grafana/provisioning:/etc/grafana/provisioning:ro
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
      - loki
    networks:
      - factory-network

networks:
  factory-network:
    driver: bridge

volumes:
  postgres-data:
  redis-data:
  rabbitmq-data:
  minio-data:
  prometheus-data:
  loki-data:
  grafana-data:
  workspaces:
  artifacts:
```

## 22.1 Langfuse

Recomenda-se utilizar o Docker Compose oficial do Langfuse em um arquivo separado:

```bash
docker compose -f docker-compose.yml \
  -f docker-compose.langfuse.yml up -d
```

Isso evita misturar a composição principal com as dependências internas do Langfuse.

---

# 23. Configuração dos agentes

## 23.1 Registro

```yaml
agents:
  - id: product.requirements
    worker: product
    enabled: true
    config: agents/definitions/product/requirements.yaml

  - id: architecture.solution
    worker: architecture
    enabled: true
    config: agents/definitions/architecture/solution.yaml

  - id: engineering.backend
    worker: engineering
    enabled: true
    config: agents/definitions/engineering/backend.yaml

  - id: validation.code-review
    worker: validation
    enabled: true
    config: agents/definitions/validation/code-review.yaml

  - id: security.appsec
    worker: security
    enabled: true
    config: agents/definitions/security/appsec.yaml
```

## 23.2 Prompt base

```text
Você é o agente {agent_name}, versão {agent_version}.

OBJETIVO
{objective}

RESPONSABILIDADES
{responsibilities}

ENTRADAS AUTORIZADAS
{input_manifest}

RESTRIÇÕES
{constraints}

FERRAMENTAS AUTORIZADAS
{allowed_tools}

CRITÉRIOS DE QUALIDADE
{quality_gates}

REGRAS
1. Não execute ações fora do escopo.
2. Não invente resultados de ferramentas.
3. Diferencie fato, inferência e recomendação.
4. Cite os artefatos usados como evidência.
5. Retorne somente o schema solicitado.
6. Ao encontrar impedimento, retorne status BLOCKED.
7. Não aprove risco crítico.
8. Não exponha segredos.
```

## 23.3 Roteamento por capacidade

O orquestrador selecionará agentes com base em:

- tipo da tarefa;
- artefatos necessários;
- risco;
- stack do projeto;
- disponibilidade do worker;
- prioridade;
- ferramentas exigidas.

---

# 24. APIs iniciais

## Projetos

```http
POST   /api/v1/projects
GET    /api/v1/projects
GET    /api/v1/projects/{project_id}
PATCH  /api/v1/projects/{project_id}
```

## Demandas

```http
POST   /api/v1/projects/{project_id}/demands
GET    /api/v1/projects/{project_id}/demands
GET    /api/v1/demands/{demand_id}
```

## Workflows

```http
POST   /api/v1/demands/{demand_id}/runs
GET    /api/v1/runs/{run_id}
POST   /api/v1/runs/{run_id}/cancel
POST   /api/v1/runs/{run_id}/retry
GET    /api/v1/runs/{run_id}/timeline
```

## Tarefas

```http
GET    /api/v1/runs/{run_id}/tasks
GET    /api/v1/tasks/{task_id}
POST   /api/v1/tasks/{task_id}/retry
```

## Aprovações

```http
GET    /api/v1/approvals
GET    /api/v1/approvals/{approval_id}
POST   /api/v1/approvals/{approval_id}/approve
POST   /api/v1/approvals/{approval_id}/reject
```

## Artefatos

```http
GET    /api/v1/runs/{run_id}/artifacts
GET    /api/v1/artifacts/{artifact_id}
GET    /api/v1/artifacts/{artifact_id}/download
```

## Agentes

```http
GET    /api/v1/agents
GET    /api/v1/agents/{agent_id}
PATCH  /api/v1/agents/{agent_id}
POST   /api/v1/agents/{agent_id}/test
```

---

# 25. Eventos internos

```text
project.created
demand.created
workflow.started
workflow.paused
workflow.completed
workflow.failed

task.created
task.queued
task.started
task.completed
task.failed
task.blocked

agent.execution.started
agent.execution.completed
agent.execution.failed

tool.execution.started
tool.execution.completed
tool.execution.failed

artifact.created
artifact.versioned

finding.created
finding.resolved

approval.requested
approval.approved
approval.rejected

risk.created
risk.updated
```

---

# 26. Estratégia de testes

## 26.1 Testes unitários

- schemas;
- transições;
- roteamento;
- validadores;
- políticas;
- ferramentas;
- adaptadores.

## 26.2 Testes de contrato

- mensagens;
- APIs;
- saída dos agentes;
- schemas de artefatos;
- compatibilidade de versões.

## 26.3 Testes de integração

- PostgreSQL;
- RabbitMQ;
- Redis;
- MinIO;
- Ollama;
- sandbox;
- OpenTelemetry.

## 26.4 Testes do grafo

- caminho feliz;
- reprovação de code review;
- falha de testes;
- risco crítico;
- aprovação humana;
- retry;
- dead-letter;
- cancelamento;
- retomada.

## 26.5 Avaliação dos agentes

Cada agente deverá possuir:

- casos dourados;
- entradas inválidas;
- casos adversariais;
- critérios objetivos;
- avaliação de schema;
- avaliação de evidência;
- avaliação de aderência ao papel.

## 26.6 Testes de segurança

- prompt injection;
- path traversal;
- command injection;
- escape do sandbox;
- exposição de segredo;
- acesso a ferramenta proibida;
- manipulação de estado;
- mensagens duplicadas.

## 26.7 Testes de performance

- várias demandas;
- filas acumuladas;
- modelo lento;
- worker indisponível;
- artefatos grandes;
- banco sob concorrência.

---

# 27. Definition of Ready e Definition of Done

## Definition of Ready

Uma tarefa está pronta quando:

- objetivo está claro;
- entradas obrigatórias existem;
- dependências estão resolvidas;
- critérios de aceite estão definidos;
- agente responsável está habilitado;
- ferramentas estão disponíveis;
- riscos conhecidos estão registrados.

## Definition of Done

Uma tarefa está concluída quando:

- saída está válida no schema;
- artefatos foram persistidos;
- evidências foram registradas;
- testes aplicáveis passaram;
- findings críticos foram resolvidos;
- auditoria foi registrada;
- próximo estado foi definido;
- aprovação foi obtida quando necessária.

---

# 28. Roadmap de implementação

## Fase 0 — Fundação

- criar repositório;
- configurar Python;
- configurar lint, tipos e testes;
- criar Docker Compose básico;
- subir PostgreSQL, Redis, RabbitMQ e MinIO;
- configurar migrations;
- criar logging estruturado.

## Fase 1 — Núcleo da plataforma

- entidades;
- API de projetos e demandas;
- registro de agentes;
- tarefas;
- eventos;
- artefatos;
- auditoria;
- autenticação local.

## Fase 2 — Orquestrador

- implementar LangGraph;
- definir estado tipado;
- criar checkpoints;
- implementar roteamento;
- retries;
- interrupções;
- aprovação humana.

## Fase 3 — Primeiros agentes

Implementar inicialmente:

1. Product Owner;
2. Analista de Requisitos;
3. Arquiteto de Solução;
4. Tech Lead;
5. Desenvolvedor Backend;
6. Revisor de Código;
7. QA;
8. AppSec;
9. DevOps;
10. Documentação;
11. Orquestrador.

## Fase 4 — Ferramentas

- leitura de repositório;
- escrita de patch;
- Git;
- lint;
- testes;
- SAST;
- dependências;
- segredos;
- container build;
- geração de documentação.

## Fase 5 — Sandbox

- runner;
- imagens permitidas;
- quotas;
- timeout;
- isolamento;
- coleta de evidências.

## Fase 6 — Interface

- dashboard;
- projeto;
- demanda;
- timeline;
- tarefas;
- aprovações;
- artefatos;
- findings;
- agentes.

## Fase 7 — Observabilidade

- OpenTelemetry;
- Prometheus;
- Grafana;
- Loki;
- Langfuse;
- dashboards.

## Fase 8 — Expansão dos papéis

Adicionar os demais agentes lógicos, reutilizando workers existentes.

## Fase 9 — Robustez

- idempotência;
- dead-letter;
- recuperação;
- testes de carga;
- backup;
- restauração;
- hardening.

---

# 29. Backlog inicial

## Épico 1 — Plataforma

- Criar projeto FastAPI.
- Criar configuração central.
- Criar conexão PostgreSQL.
- Criar migrations.
- Criar autenticação.
- Criar auditoria.

## Épico 2 — Agentes

- Criar schema de definição.
- Criar registry.
- Criar runtime.
- Criar adaptador Ollama.
- Criar saída estruturada.
- Criar testes de agente.

## Épico 3 — Workflow

- Criar estado do grafo.
- Criar nós.
- Criar roteador.
- Criar checkpoints.
- Criar interrupção humana.
- Criar retries.

## Épico 4 — Workers

- Criar consumidor base.
- Criar filas.
- Criar envelope de mensagem.
- Criar idempotência.
- Criar dead-letter.
- Criar health checks.

## Épico 5 — Artefatos

- Criar cliente MinIO.
- Criar checksum.
- Criar versionamento.
- Criar manifesto.
- Criar API de download.

## Épico 6 — Engenharia

- Criar workspace Git.
- Criar leitura.
- Criar patch.
- Criar commit.
- Criar runner de lint.
- Criar runner de teste.

## Épico 7 — Segurança

- Integrar Bandit.
- Integrar pip-audit.
- Integrar Gitleaks.
- Integrar Trivy.
- Criar policy gate.

## Épico 8 — Observabilidade

- Instrumentar API.
- Instrumentar workers.
- Criar métricas.
- Criar dashboards.
- Integrar Langfuse.

---

# 30. Comandos para iniciar

## 30.1 Pré-requisitos

- Docker Desktop;
- Docker Compose;
- Git;
- Make;
- Python 3.12 opcional no host;
- Ollama no host.

## 30.2 Instalação do modelo

```bash
ollama pull qwen2.5-coder:7b
ollama pull llama3.1:8b
```

## 30.3 Inicialização

```bash
cp .env.example .env
docker compose up -d postgres redis rabbitmq minio
docker compose run --rm api alembic upgrade head
docker compose up -d
```

## 30.4 Comandos Make sugeridos

```makefile
.PHONY: setup up down logs test lint typecheck security migrate seed clean

setup:
	cp -n .env.example .env || true
	docker compose pull
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

test:
	docker compose run --rm api pytest -q

lint:
	docker compose run --rm api ruff check .

format:
	docker compose run --rm api ruff format .

typecheck:
	docker compose run --rm api mypy .

security:
	docker compose run --rm security-worker ./scripts/security-check.sh

migrate:
	docker compose run --rm api alembic upgrade head

migration:
	docker compose run --rm api alembic revision --autogenerate -m "$(name)"

seed:
	docker compose run --rm api python -m app.db.seed

clean:
	docker compose down -v --remove-orphans
```

## 30.5 Endereços locais

| Serviço | Endereço |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| RabbitMQ | http://localhost:15672 |
| MinIO | http://localhost:9001 |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |
| Ollama | http://localhost:11434 |

---

# 31. Critérios de sucesso

A primeira versão será considerada bem-sucedida quando:

- uma demanda puder ser criada pela API;
- o workflow puder ser iniciado;
- pelo menos dez agentes participarem do fluxo;
- as tarefas forem distribuídas por RabbitMQ;
- o estado sobreviver a reinício;
- artefatos forem armazenados no MinIO;
- o desenvolvedor gerar um patch;
- o revisor puder rejeitar o patch;
- os testes forem executados em sandbox;
- o AppSec gerar findings;
- uma aprovação humana pausar e retomar o fluxo;
- logs, métricas e traces estiverem disponíveis;
- todo resultado puder ser rastreado até sua entrada.

---

# 32. Evoluções futuras

- Temporal para workflows de longa duração.
- Camunda para BPMN e processos corporativos.
- Kubernetes.
- vLLM com GPU.
- Gitea ou GitLab local.
- pgvector.
- MCP para ferramentas.
- A2A para agentes distribuídos.
- Vault.
- OPA para políticas.
- Keycloak.
- catálogo de agentes.
- marketplace interno de ferramentas.
- avaliação contínua de prompts.
- múltiplos modelos.
- seleção automática de modelo.
- execução remota de sandboxes.
- ambientes por projeto.

---

# 33. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Loop infinito entre agentes | Limite de tentativas e revisão humana |
| Código inseguro | Sandbox e scanners |
| Alucinação | Saídas estruturadas e ferramentas determinísticas |
| Contexto excessivo | Context builder e resumos |
| Agentes com funções sobrepostas | Contratos e ownership |
| Estado inconsistente | PostgreSQL como fonte de verdade |
| Mensagens duplicadas | Idempotência |
| Prompt injection | Separação de instruções, validação e menor privilégio |
| Alto consumo de recursos | Limites por container e filas |
| Modelo local insuficiente | Fallback configurável |
| Falta de rastreabilidade | Eventos e artefatos versionados |
| Complexidade inicial | Implementação incremental |
| Dependências vulneráveis | Scanners e versões fixadas |
| Segredos no repositório | Gitleaks e política de segredos |
| Aprovação automática indevida | Gates humanos obrigatórios |

---

# 34. Decisões arquiteturais iniciais

## ADR-001 — LangGraph

**Decisão:** utilizar LangGraph como orquestrador dos agentes.

**Motivo:** suporte a estado, rotas condicionais, checkpoints, interrupções e human-in-the-loop.

## ADR-002 — Ollama no host

**Decisão:** executar Ollama diretamente no host, especialmente em macOS Apple Silicon.

**Motivo:** simplificar acesso ao hardware local e reduzir sobrecarga.

## ADR-003 — RabbitMQ

**Decisão:** usar RabbitMQ como broker principal.

**Motivo:** filas especializadas, confirmação, roteamento e dead-letter.

## ADR-004 — PostgreSQL

**Decisão:** usar PostgreSQL como fonte de verdade.

**Motivo:** transações, integridade, auditoria e flexibilidade.

## ADR-005 — MinIO

**Decisão:** usar MinIO para artefatos.

**Motivo:** API compatível com S3 e execução local.

## ADR-006 — Workers por domínio

**Decisão:** agrupar agentes em workers por domínio.

**Motivo:** reduzir complexidade operacional inicial.

## ADR-007 — Sandbox efêmero

**Decisão:** toda execução de código ocorrerá em ambiente isolado.

**Motivo:** segurança e reprodutibilidade.

## ADR-008 — Configuração declarativa

**Decisão:** agentes serão definidos em YAML e schemas.

**Motivo:** versionamento, governança e facilidade de evolução.

---

# 35. Checklist para início do desenvolvimento

## Arquitetura

- [ ] Aprovar componentes.
- [ ] Aprovar agrupamento de workers.
- [ ] Criar ADRs.
- [ ] Definir requisitos de hardware.
- [ ] Definir modelos locais iniciais.

## Repositório

- [ ] Criar monorepo.
- [ ] Configurar branches.
- [ ] Configurar hooks.
- [ ] Configurar lint.
- [ ] Configurar testes.

## Infraestrutura

- [ ] Criar Docker Compose.
- [ ] Criar volumes.
- [ ] Criar rede.
- [ ] Criar health checks.
- [ ] Criar `.env.example`.

## Banco

- [ ] Criar entidades.
- [ ] Criar migrations.
- [ ] Criar seed.
- [ ] Criar auditoria.

## Agentes

- [ ] Criar schema.
- [ ] Criar registry.
- [ ] Criar agente de requisitos.
- [ ] Criar agente de arquitetura.
- [ ] Criar agente de desenvolvimento.
- [ ] Criar agente revisor.
- [ ] Criar agente QA.
- [ ] Criar agente AppSec.
- [ ] Criar agente DevOps.
- [ ] Criar agente de documentação.

## Workflow

- [ ] Criar grafo principal.
- [ ] Criar estados.
- [ ] Criar transições.
- [ ] Criar retries.
- [ ] Criar aprovação humana.
- [ ] Criar cancelamento.

## Ferramentas

- [ ] Criar leitura de Git.
- [ ] Criar patch.
- [ ] Criar lint.
- [ ] Criar testes.
- [ ] Criar scanners.
- [ ] Criar sandbox.

## Observabilidade

- [ ] Criar logs JSON.
- [ ] Criar métricas.
- [ ] Criar traces.
- [ ] Criar dashboards.
- [ ] Integrar Langfuse.

## Segurança

- [ ] Definir permissões.
- [ ] Proteger segredos.
- [ ] Limitar containers.
- [ ] Validar prompts.
- [ ] Criar trilha de auditoria.

---

# Conclusão

A solução proposta atende a todos os papéis da fábrica por meio de agentes lógicos configuráveis, sem exigir um container para cada cargo. A execução inicial é mantida administrável usando workers agrupados por domínio.

A arquitetura combina:

- LangGraph para fluxo e estado;
- Ollama para inferência local;
- FastAPI para APIs;
- PostgreSQL para persistência;
- RabbitMQ para distribuição;
- Redis para cache e locks;
- MinIO para artefatos;
- Docker Compose para execução;
- Langfuse e OpenTelemetry para observabilidade;
- containers efêmeros para execução segura de código.

A recomendação é começar pelo fluxo principal com aproximadamente dez agentes, validar os contratos e os quality gates e, em seguida, habilitar progressivamente todos os papéis descritos neste documento.
