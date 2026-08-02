"""Testes de resolução de nome de modelo (regressão: Ollama retorna 404 quando
o nome do modelo não inclui a tag exata instalada, ex.: "qwen2.5-coder" vs
"qwen2.5-coder:7b")."""
from agents.runtime.ollama_client import resolve_model_name


def test_resolve_known_model_without_tag():
    assert resolve_model_name("qwen2.5-coder") == "qwen2.5-coder:7b"
    assert resolve_model_name("llama3.1") == "llama3.1:8b"


def test_resolve_model_with_tag_is_unchanged():
    assert resolve_model_name("qwen2.5-coder:7b") == "qwen2.5-coder:7b"
    assert resolve_model_name("llama3.1:8b") == "llama3.1:8b"
    assert resolve_model_name("mariana-llama:latest") == "mariana-llama:latest"


def test_resolve_unknown_model_is_unchanged():
    assert resolve_model_name("mistral") == "mistral"
