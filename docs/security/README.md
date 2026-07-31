# Segurança

- Autenticação local: Argon2id + JWT curto + refresh rotativo (seção 20.1)
- Papéis: ADMIN, FACTORY_MANAGER, APPROVER, DEVELOPER, AUDITOR, VIEWER (20.2)
- Segredos: `.env` somente em desenvolvimento; nunca versionar (20.3)
- Prompts: instruções separadas de dados; conteúdo externo marcado como não
  confiável; saída estruturada obrigatória (20.4)
- Auditoria append-only na tabela `audit_events` (20.5)
- Sandbox: ver `sandbox/policies/sandbox-policy.yaml` (seção 16)
