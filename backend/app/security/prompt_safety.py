"""Segurança dos prompts (seção 20.4): separação de instruções e conteúdo externo."""

UNTRUSTED_OPEN = "<conteudo_nao_confiavel>"
UNTRUSTED_CLOSE = "</conteudo_nao_confiavel>"


def mark_untrusted(content: str) -> str:
    """Marca conteúdo externo como não confiável antes de entrar em um prompt."""
    sanitized = content.replace(UNTRUSTED_OPEN, "").replace(UNTRUSTED_CLOSE, "")
    return f"{UNTRUSTED_OPEN}\n{sanitized}\n{UNTRUSTED_CLOSE}"
