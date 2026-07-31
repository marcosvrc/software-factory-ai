"""Policy gate de segurança (Épico 7): decide aprovação a partir dos findings.

Gate 7 (seção 18): SAST aprovado; dependências avaliadas; imagem analisada;
licenças avaliadas; nenhum risco crítico aberto.
"""
SEVERITY_ORDER = ["info", "low", "medium", "high", "critical"]


def evaluate(findings: list[dict], *, max_severity: str = "medium") -> dict:
    threshold = SEVERITY_ORDER.index(max_severity)
    violations = [
        f for f in findings
        if SEVERITY_ORDER.index(f.get("severity", "info")) > threshold
    ]
    return {
        "approved": not violations,
        "violations": violations,
        "policy": f"nenhum finding acima de {max_severity}",
    }
