"""Run the Glean API on one dual-stack socket ([::]:PORT that also accepts IPv4).

`uvicorn --host ::` lets asyncio set IPV6_V6ONLY, so IPv4 clients get "connection
refused". Railway's private network is IPv6; local Docker networks are IPv4.
"""
import os
import socket

import uvicorn

port = int(os.environ.get("PORT") or 8000)
sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
sock.bind(("::", port))
sock.listen(2048)
sock.set_inheritable(True)
print(f"[glean] API listening on [::]:{port} (IPv4 and IPv6)", flush=True)
uvicorn.run(
    "glean_api.main:app",
    fd=sock.fileno(),
    proxy_headers=True,
    forwarded_allow_ips="*",
    server_header=False,
)
