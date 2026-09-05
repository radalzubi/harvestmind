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
    socks = []
    for family, host in ((socket.AF_INET, "0.0.0.0"), (socket.AF_INET6, "::")):  # noqa: S104 - container bind, auth enforced
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
