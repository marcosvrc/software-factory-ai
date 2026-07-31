# Agentes lógicos

53 agentes definidos em `agents/definitions/<dominio>/*.yaml`, seguindo o
contrato da seção 11 (id, nome, versão, domínio, objetivo, entradas, schema de
saída, artefatos, ferramentas permitidas/proibidas, modelo, gates, retry e
escalonamento). O registry (`agents/registry.yaml`) mapeia agente → worker.

O orquestrador sincroniza as definições para a tabela `agent_definitions` no
startup; habilite/desabilite agentes via `PATCH /api/v1/agents/{id}`.
