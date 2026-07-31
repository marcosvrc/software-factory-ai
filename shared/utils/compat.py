"""Compatibilidade: StrEnum existe a partir do Python 3.11 (alvo do projeto é 3.12+)."""
try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - somente para interpretes antigos
    from enum import Enum

    class StrEnum(str, Enum):
        def __str__(self) -> str:
            return str(self.value)


__all__ = ["StrEnum"]
