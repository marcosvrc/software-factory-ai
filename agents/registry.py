"""Registro de agentes lógicos (seções 8.1, 11 e 23.1).

Carrega `agents/registry.yaml` e as definições YAML, validando os elementos
obrigatórios do contrato (seção 11.2).
"""
from pathlib import Path

import yaml

from shared.exceptions import AgentDefinitionError

REQUIRED_FIELDS = [
    "id",
    "name",
    "version",
    "domain",
    "objective",
    "inputs",
    "outputs",
    "tools",
    "model",
    "quality_gates",
    "retry",
    "escalation",
]

BASE_DIR = Path(__file__).parent


class AgentRegistry:
    def __init__(self, definitions: dict[str, dict]) -> None:
        self._definitions = definitions

    @classmethod
    def load_default(cls) -> "AgentRegistry":
        return cls.load(BASE_DIR / "registry.yaml")

    @classmethod
    def load(cls, registry_path: Path) -> "AgentRegistry":
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        definitions: dict[str, dict] = {}
        for entry in registry.get("agents", []):
            config_path = registry_path.parent.parent / entry["config"]
            definition = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            validate_definition(definition)
            definition["enabled"] = entry.get("enabled", True)
            definition["worker"] = entry.get("worker", definition["domain"])
            definitions[definition["id"]] = definition
        return cls(definitions)

    def get(self, agent_id: str) -> dict | None:
        return self._definitions.get(agent_id)

    def all(self) -> list[dict]:
        return list(self._definitions.values())

    def by_domain(self, domain: str) -> list[dict]:
        return [d for d in self._definitions.values() if d["domain"] == domain]


def validate_definition(definition: dict) -> None:
    """Valida os elementos obrigatórios do contrato (seção 11.2)."""
    missing = [f for f in REQUIRED_FIELDS if f not in definition]
    if missing:
        raise AgentDefinitionError(
            f"Definição {definition.get('id', '?')} sem campos obrigatórios: {missing}"
        )
    if "required" not in definition["inputs"]:
        raise AgentDefinitionError(f"{definition['id']}: inputs.required ausente")
    if "allowed" not in definition["tools"] or "denied" not in definition["tools"]:
        raise AgentDefinitionError(f"{definition['id']}: tools.allowed/denied ausentes")
    if "schema" not in definition["outputs"]:
        raise AgentDefinitionError(f"{definition['id']}: outputs.schema ausente")
