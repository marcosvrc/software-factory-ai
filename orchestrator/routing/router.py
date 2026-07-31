"""Roteamento por capacidade (seção 23.3): seleção de agentes por etapa.

Critérios: tipo da tarefa, artefatos necessários, risco, stack, disponibilidade
do worker, prioridade e ferramentas exigidas.
"""
from agents.registry import AgentRegistry

# Mapeamento etapa do fluxo -> agentes lógicos (fluxo da seção 9)
STAGE_AGENTS: dict[str, list[str]] = {
    "triage": ["governance.flow-manager"],
    "product_discovery": [
        "product.product-manager",
        "product.product-owner",
        "product.business-analyst",
        "product.ux-researcher",
    ],
    "requirements": ["product.requirements-analyst", "product.ux-ui-designer"],
    "architecture": [
        "architecture.solution",
        "architecture.software",
        "architecture.data",
        "architecture.integration",
        "architecture.security",
    ],
    "technical_planning": ["architecture.tech-lead", "governance.engineering-manager"],
    "development": ["engineering.backend"],
    "code_review": ["engineering.code-reviewer"],
    "automated_tests": ["validation.test-automation"],
    "functional_qa": ["validation.qa-lead", "validation.functional-qa"],
    "security_compliance": [
        "security.appsec",
        "security.open-source",
        "security.privacy",
    ],
    "operational_validation": ["operations.devops", "operations.sre"],
    "documentation_release": ["delivery.documentation", "delivery.release-manager"],
}

# Fila por domínio (seção 13.3)
DOMAIN_QUEUE = {
    "product": "factory.product",
    "architecture": "factory.architecture",
    "engineering": "factory.engineering",
    "validation": "factory.validation",
    "security": "factory.security",
    "operations": "factory.operations",
    "delivery": "factory.delivery",
    "governance": "factory.governance",
}


class CapabilityRouter:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    def agents_for_stage(self, stage: str) -> list[dict]:
        """Retorna definições habilitadas dos agentes da etapa."""
        selected = []
        for agent_id in STAGE_AGENTS.get(stage, []):
            definition = self.registry.get(agent_id)
            if definition is not None and definition.get("enabled", True):
                selected.append(definition)
        return selected

    @staticmethod
    def queue_for(definition: dict) -> str:
        return DOMAIN_QUEUE[definition["domain"]]
