"""Adaptador Ollama (camada de modelo, seção 5.2): inferência local com fallback."""
import json
import os

import httpx

from shared.logging import get_logger

logger = get_logger("agents.ollama")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

# Mapa de compatibilidade: as definições de agentes referenciam modelos sem
# tag (ex.: "qwen2.5-coder"), mas o Ollama exige o nome exato do modelo
# instalado (ex.: "qwen2.5-coder:7b"), retornando 404 em caso de divergência.
DEFAULT_MODEL_TAGS = {
    "qwen2.5-coder": "qwen2.5-coder:7b",
    "llama3.1": "llama3.1:8b",
}


def resolve_model_name(model: str) -> str:
    """Resolve um nome de modelo sem tag para o nome completo instalado."""
    if ":" in model:
        return model
    return DEFAULT_MODEL_TAGS.get(model, model)


class OllamaClient:
    def __init__(self, base_url: str | None = None, timeout: float = 600.0) -> None:
        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout

    async def chat_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_context_tokens: int = 32000,
    ) -> dict:
        """Chamada de chat com saída JSON estruturada (format=json)."""
        resolved_model = resolve_model_name(model)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": resolved_model,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": temperature, "num_ctx": max_context_tokens},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
        content = data.get("message", {}).get("content", "{}")
        usage = int(data.get("prompt_eval_count", 0)) + int(data.get("eval_count", 0))
        try:
            return {"content": json.loads(content), "token_usage": usage}
        except json.JSONDecodeError as exc:
            raise ValueError(f"Resposta do modelo não é JSON válido: {content[:200]}") from exc
