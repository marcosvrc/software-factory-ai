# Runbook local

- Subir: `make setup && make migrate && make seed && make up`
- Logs: `make logs`
- Filas: http://localhost:15672 (factory/factory)
- Dead-letter: fila `factory.dead-letter`
- Estado de um run: `GET /api/v1/runs/{id}` + `/timeline`
- Retomada após reinício: o orquestrador retoma runs `QUEUED/RETRYING` via polling
