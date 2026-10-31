"""Runs the PSI library for the engine, one JSON line in, one JSON line out.

The OpenMined PSI library has no Windows build, so on Windows this file runs
inside WSL (Linux) and the engine talks to it through a pipe on this laptop.
The network between the two laptops is handled by the engine, not here.
This file only does the maths. It never opens a socket.

Each line in is {"id", "op", ...}. Each line out is {"id", "ok", ...}.
"""
import base64
import json
import sys

import private_set_intersection.python as psi

FALSE_POSITIVE_RATE = 1e-9
_objects: dict = {}


def _encode(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _parse(kind, text: str):
    message = kind()
    message.ParseFromString(base64.b64decode(text))
    return message


def handle(message: dict) -> dict:
    op = message["op"]
    if op == "ping":
        return {}
    if op == "server_setup":
        server = psi.server.CreateWithNewKey(bool(message["reveal"]))
        setup = server.CreateSetupMessage(
            FALSE_POSITIVE_RATE, int(message["count"]), list(message["items"]), psi.DataStructure.GCS)
        _objects["server"] = server
        return {"setup": _encode(setup.SerializeToString())}
    if op == "server_process":
        response = _objects["server"].ProcessRequest(_parse(psi.Request, message["request"]))
        return {"response": _encode(response.SerializeToString())}
    if op == "client_request":
        client = psi.client.CreateWithNewKey(bool(message["reveal"]))
        _objects["client"] = client
        return {"request": _encode(client.CreateRequest(list(message["items"])).SerializeToString())}
    if op == "client_finish":
        setup, response = _parse(psi.ServerSetup, message["setup"]), _parse(psi.Response, message["response"])
        client = _objects["client"]
        if message["reveal"]:
            return {"indices": [int(i) for i in client.GetIntersection(setup, response)]}
        return {"size": int(client.GetIntersectionSize(setup, response))}
    raise ValueError(f"unknown op {op!r}")


def main() -> None:
    print(json.dumps({"ready": True}), flush=True)
    for line in sys.stdin:
        if not line.strip():
            continue
        message = json.loads(line)
        try:
            reply = {"ok": True, **handle(message)}
        except Exception as error:
            reply = {"ok": False, "error": f"{type(error).__name__}: {error}"}
        print(json.dumps({"id": message.get("id"), **reply}), flush=True)


if __name__ == "__main__":
    main()
