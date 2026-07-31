#!/usr/bin/env bash
# Verificações de segurança do próprio repositório (Épico 7).
set -uo pipefail
status=0
echo "== bandit (SAST) =="
bandit -r backend/app orchestrator agents workers tools shared -q || status=1
echo "== pip-audit (dependências) =="
pip-audit -r backend/requirements.txt || status=1
echo "== gitleaks (segredos) =="
if command -v gitleaks >/dev/null; then gitleaks detect --source . || status=1; else echo "gitleaks não instalado"; fi
echo "== trivy (filesystem) =="
if command -v trivy >/dev/null; then trivy fs --exit-code 1 . || status=1; else echo "trivy não instalado"; fi
exit $status
