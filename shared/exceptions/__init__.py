"""Exceções compartilhadas da fábrica."""


class FactoryError(Exception):
    """Erro base da plataforma."""


class ConfigurationError(FactoryError):
    """Configuração ausente ou inválida."""


class AgentDefinitionError(FactoryError):
    """Definição de agente inválida (contrato da seção 11)."""


class ToolNotAllowedError(FactoryError):
    """Agente tentou usar ferramenta fora da lista permitida (menor privilégio, 3.6)."""


class ToolExecutionError(FactoryError):
    """Falha na execução de uma ferramenta."""


class SandboxViolationError(FactoryError):
    """Violação das proibições do sandbox (seção 16.4)."""


class SchemaValidationError(FactoryError):
    """Saída do agente não aderente ao schema (seção 11.3)."""


class ApprovalRequiredError(FactoryError):
    """Ação exige aprovação humana (seção 17)."""


class MaxCyclesExceededError(FactoryError):
    """Limite de 3 ciclos automáticos por gate excedido (seção 9.1)."""
