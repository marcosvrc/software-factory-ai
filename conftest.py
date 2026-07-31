"""Configuração de testes: raiz e backend no sys.path (monorepo)."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
for path in (ROOT, ROOT / "backend"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
