"""Serve the API on IPv4 and IPv6 at once.

Fly's proxy and health checks reach the machine over IPv4; the solver
machines reach it over the IPv6 private network (6PN). Uvicorn takes one
host, and a bare ``::`` bind is v6-only on the Fly guest, so two sockets
are bound here and handed to uvicorn.
"""
from __future__ import annotations

import os
import socket
import sys

import uvicorn


def main() -> int:
    port = int(os.environ.get("PORT", "8000"))
    # The bind scope is declared by the launcher (HARVESTMIND_BIND_HOST), never assumed. Loopback
    # binds loopback only; the wildcard is accepted only when the app runs in an authenticated
    # deployment env (api.dependencies refuses a permissive wildcard at startup).
    declared = os.environ.get("HARVESTMIND_BIND_HOST", "127.0.0.1").strip()
    if declared in ("127.0.0.1", "localhost", "::1"):
        binds = ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1"))
    elif declared in ("0.0.0.0", "::"):  # noqa: S104  # nosec B104 - comparison with the declared scope, bind below
        binds = ((socket.AF_INET, "0.0.0.0"), (socket.AF_INET6, "::"))  # noqa: S104  # nosec B104 - explicit deployment opt-in
    else:
        print(f"serve: HARVESTMIND_BIND_HOST={declared!r} is not a supported bind scope", file=sys.stderr)
        return 1
    socks = []
    for family, host in binds:
        try:
            s = socket.socket(family, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if family == socket.AF_INET6:
                s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            s.bind((host, port))
            s.listen(2048)
            s.setblocking(False)
            socks.append(s)
        except OSError as exc:
            print(f"serve: could not bind {host}:{port}: {exc}", file=sys.stderr)
    if not socks:
        return 1
    config = uvicorn.Config("api.main:app", port=port, proxy_headers=True, forwarded_allow_ips="*", log_level="info")
    server = uvicorn.Server(config)
    server.run(sockets=socks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
