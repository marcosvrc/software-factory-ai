#!/usr/bin/env bash
# Cria o bucket de artefatos da fábrica (Épico 5).
set -euo pipefail
mc alias set factory "http://${MINIO_ENDPOINT:-minio:9000}" \
  "${MINIO_ACCESS_KEY:-factory}" "${MINIO_SECRET_KEY:-local-development-password}"
mc mb --ignore-existing factory/factory
echo "bucket pronto"
