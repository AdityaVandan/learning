"""
TRACE / CONNECT examples: rarely used in typical REST APIs, but part of HTTP.

Many production APIs disable TRACE for security reasons. CONNECT is generally used by
proxies to establish tunnels.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from common import register_example

router = APIRouter(prefix="/verbs", tags=["TRACE & CONNECT"])


@router.api_route("/trace", methods=["TRACE"])
async def trace_echo(request: Request):
    """
    TRACE is a diagnostic method that echoes the received request.
    This demo returns the request line + headers as text.
    """

    lines: list[str] = []
    lines.append(f"{request.method} {request.url.path} HTTP/{request.scope.get('http_version','1.1')}")
    for k, v in request.headers.items():
        lines.append(f"{k}: {v}")
    return PlainTextResponse("\n".join(lines), media_type="message/http")


register_example(
    verb="TRACE",
    name="TRACE echo (diagnostic)",
    path="/verbs/trace",
    methods=["TRACE"],
    semantics=["safe (conceptually)", "diagnostic", "often disabled"],
    scenario="Echo received request headers for debugging/proxy visibility",
)


@router.api_route("/connect", methods=["CONNECT"])
async def connect_demo():
    """
    CONNECT is generally used to establish a tunnel through a proxy.
    In a typical REST API server, there's nothing meaningful to do with it.
    """

    return PlainTextResponse("CONNECT is proxy/tunnel specific; not supported here.", status_code=501)


register_example(
    verb="CONNECT",
    name="CONNECT (not supported)",
    path="/verbs/connect",
    methods=["CONNECT"],
    semantics=["proxy-tunneling", "not typical for REST APIs"],
    scenario="Show that CONNECT is usually unsupported by app servers",
)

