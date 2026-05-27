"""
1xx Informational responses.

Reference: ../ResponseCodes.md § 1xx
"""

from fastapi import APIRouter, Header, Request, WebSocket
from fastapi.responses import JSONResponse, Response

from common import register_example

router = APIRouter(prefix="/codes", tags=["1xx Informational"])


@router.post("/100")
async def code_100_continue(
    request: Request,
    expect: str | None = Header(default=None, alias="Expect"),
):
    """
    100 Continue — interim response before the client sends a large body.

    Real scenario: uploads where the server validates headers first (Expect: 100-continue).

    This demo: if `Expect: 100-continue` is present, we return 100; otherwise 200 with guidance.

    curl -X POST http://127.0.0.1:8000/codes/100 -H "Expect: 100-continue" -d "body"
    """
    if expect and "100-continue" in expect.lower():
        # ASGI/clients may not show interim responses uniformly; status 100 is still valid HTTP.
        return Response(status_code=100)
    return JSONResponse(
        status_code=200,
        content={
            "hint": "Send header Expect: 100-continue to trigger a 100 response.",
            "note": "Many HTTP clients hide interim 1xx responses; use curl -v to inspect.",
        },
    )


register_example(
    code=100,
    name="Continue",
    path="/codes/100",
    methods=["POST"],
    scenario="Expect: 100-continue triggers interim 100",
)


@router.websocket("/101/ws")
async def code_101_switching_protocols(websocket: WebSocket):
    """
    101 Switching Protocols — upgrade from HTTP to another protocol (e.g. WebSocket).

    Real scenario: client sends Upgrade: websocket; server completes handshake with 101.

    curl cannot demo WebSockets easily — use a browser or: wscat -c ws://127.0.0.1:8000/codes/101/ws
    """
    await websocket.accept()
    await websocket.send_json(
        {
            "status": 101,
            "message": "WebSocket upgrade succeeded (Switching Protocols).",
        }
    )
    await websocket.close()


register_example(
    code=101,
    name="Switching Protocols",
    path="/codes/101/ws",
    methods=["WEBSOCKET"],
    scenario="WebSocket upgrade handshake",
)


@router.get("/102")
async def code_102_processing():
    """
    102 Processing — long operation accepted; client should not time out (WebDAV).

    Real scenario: multi-step server work where you return 102 while work continues.

    curl http://127.0.0.1:8000/codes/102
    """
    return JSONResponse(
        status_code=102,
        content={
            "message": "Request accepted; processing continues on the server.",
            "retry": "Poll GET /codes/202/jobs/demo-job later for async pattern.",
        },
    )


register_example(
    code=102,
    name="Processing",
    path="/codes/102",
    methods=["GET"],
    scenario="Long-running work still in progress",
)


@router.get("/103")
async def code_103_early_hints():
    """
    103 Early Hints — preload hints before the final response (HTTP/2+).

    Real scenario: send Link headers early so the browser can prefetch assets.

    True streaming early hints need ASGI/server support; here we return 103 with Link once.

    curl -v http://127.0.0.1:8000/codes/103
    """
    return Response(
        status_code=103,
        headers={
            "Link": '</static/app.js>; rel=preload; as=script',
        },
        content=b"",
    )


register_example(
    code=103,
    name="Early Hints",
    path="/codes/103",
    methods=["GET"],
    scenario="Preload Link headers before final response",
)
