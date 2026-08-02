"""Servidor MCP falso para os testes do cliente (transporte stdio).

Modos:
- ok:        handshake + tools/list normais
- noisy:     escreve logs não-JSON em stdout antes das respostas
- rpc_error: responde tools/list com erro JSON-RPC
- exit:      encerra imediatamente, sem responder
- hang:      aceita a mensagem e nunca responde (exercita o timeout)
"""
import json
import sys
import time

TOOLS = [
    {
        "name": "beta_tool",
        "description": "Ferramenta beta",
        "inputSchema": {"type": "object", "properties": {"q": {"type": "string"}}},
    },
    {
        "name": "alpha_tool",
        "description": "Ferramenta alpha",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def send(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "ok"
    if mode == "exit":
        return

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            continue

        method = message.get("method")
        request_id = message.get("id")

        if mode == "hang" and method == "initialize":
            time.sleep(30)
            return

        if mode == "noisy":
            sys.stdout.write("log: processando " + str(method) + "\n")
            sys.stdout.flush()

        if method == "initialize":
            send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "fake-server", "version": "9.9.9"},
                    },
                }
            )
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            if mode == "rpc_error":
                send(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": "Method not found"},
                    }
                )
            else:
                send({"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}})
            return
        elif request_id is not None:
            send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": "Method not found"},
                }
            )


if __name__ == "__main__":
    main()
