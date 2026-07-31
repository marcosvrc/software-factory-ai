# Sandbox de execução segura

Implementa a seção 16 da proposta. Construa a imagem aprovada:

```bash
docker build -t factory-sandbox-python:latest sandbox/images/python
```

O runner usa a API Docker do host. Em desenvolvimento local, para permitir que o
`engineering-worker` crie containers efêmeros, adicione ao serviço no
`docker-compose.yml` (decisão local consciente — o *sandbox* em si continua sem
socket, sem rede e sem root, conforme 16.4):

```yaml
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

Alternativa mais segura: executar um proxy de socket (ex.: tecnativa/docker-socket-proxy)
limitado a `containers`. O container efêmero criado pelo runner nunca recebe o socket.
