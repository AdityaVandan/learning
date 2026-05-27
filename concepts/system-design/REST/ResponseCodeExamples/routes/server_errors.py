"""
5xx Server error responses.

Reference: ../ResponseCodes.md § 5xx
"""

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

import common
from common import register_example

router = APIRouter(prefix="/codes", tags=["5xx Server Errors"])


@router.get("/500")
async def code_500_internal_server_error(crash: bool = False):
    """
    500 Internal Server Error — unexpected failure; no more specific 5xx fits.

    curl "http://127.0.0.1:8000/codes/500?crash=true"
    """
    if crash:
        raise RuntimeError("Simulated unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"error": "Simulated internal failure (pass ?crash=true for exception)"},
    )


register_example(
    code=500,
    name="Internal Server Error",
    path="/codes/500",
    methods=["GET"],
    scenario="Explicit 500 or ?crash=true raises exception",
)


@router.get("/501/legacy-feature")
async def code_501_not_implemented():
    """
    501 Not Implemented — server does not support this capability.

    curl http://127.0.0.1:8000/codes/501/legacy-feature
    """
    return JSONResponse(
        status_code=501,
        content={"error": "SOAP gateway not implemented in this REST service"},
    )


register_example(
    code=501,
    name="Not Implemented",
    path="/codes/501/legacy-feature",
    methods=["GET"],
    scenario="Unsupported legacy capability",
)


@router.get("/502")
async def code_502_bad_gateway(simulate: bool = True):
    """
    502 Bad Gateway — gateway/proxy got invalid response from upstream.

    curl http://127.0.0.1:8000/codes/502
    """
    if simulate:
        return JSONResponse(
            status_code=502,
            content={
                "error": "Upstream returned invalid JSON",
                "upstream": "fake-payment-service",
            },
        )
    return {"status": "ok"}


register_example(
    code=502,
    name="Bad Gateway",
    path="/codes/502",
    methods=["GET"],
    scenario="Upstream returned malformed response",
)


@router.get("/503")
async def code_503_service_unavailable():
    """
    503 Service Unavailable — maintenance or overload; Retry-After guides clients.

    Toggle: POST /admin/maintenance?enabled=true

    curl http://127.0.0.1:8000/codes/503
    """
    if common.maintenance_mode:
        return JSONResponse(
            status_code=503,
            headers={"Retry-After": "300"},
            content={"error": "Scheduled maintenance", "retry_after_seconds": 300},
        )
    return {"maintenance_mode": False, "hint": "POST /admin/maintenance?enabled=true"}


register_example(
    code=503,
    name="Service Unavailable",
    path="/codes/503",
    methods=["GET"],
    scenario="Maintenance mode enabled via /admin/maintenance",
)


@router.post("/admin/maintenance")
async def toggle_maintenance(enabled: bool):
    """Helper to flip global maintenance flag for 503 demos."""
    common.maintenance_mode = enabled
    return {"maintenance_mode": common.maintenance_mode}


@router.get("/504")
async def code_504_gateway_timeout():
    """
    504 Gateway Timeout — gateway timed out waiting for upstream.

    curl http://127.0.0.1:8000/codes/504
    """
    return JSONResponse(
        status_code=504,
        content={"error": "Upstream did not respond within 30s", "upstream": "search-index"},
    )


register_example(
    code=504,
    name="Gateway Timeout",
    path="/codes/504",
    methods=["GET"],
    scenario="Upstream exceeded gateway timeout",
)


@router.get("/505")
async def code_505_http_version_not_supported():
    """
    505 HTTP Version Not Supported — server rejects the request HTTP version.

    curl http://127.0.0.1:8000/codes/505
    """
    return JSONResponse(
        status_code=505,
        content={"error": "HTTP/0.9 not supported; use HTTP/1.1 or HTTP/2"},
    )


register_example(
    code=505,
    name="HTTP Version Not Supported",
    path="/codes/505",
    methods=["GET"],
    scenario="Unsupported HTTP version",
)


@router.get("/506")
async def code_506_variant_also_negotiates():
    """
    506 Variant Also Negotiates — content negotiation configuration error (rare).

    curl http://127.0.0.1:8000/codes/506
    """
    return JSONResponse(
        status_code=506,
        content={"error": "Recursive content negotiation on variant resource"},
    )


register_example(
    code=506,
    name="Variant Also Negotiates",
    path="/codes/506",
    methods=["GET"],
    scenario="Negotiation loop misconfiguration",
)


@router.post("/507")
async def code_507_insufficient_storage():
    """
    507 Insufficient Storage — cannot store representation (WebDAV).

    curl -X POST http://127.0.0.1:8000/codes/507
    """
    return JSONResponse(
        status_code=507,
        content={"error": "Storage quota exceeded for user workspace"},
    )


register_example(
    code=507,
    name="Insufficient Storage",
    path="/codes/507",
    methods=["POST"],
    scenario="WebDAV quota exceeded",
)


@router.get("/508")
async def code_508_loop_detected():
    """
    508 Loop Detected — infinite redirect/propagation loop (WebDAV).

    curl http://127.0.0.1:8000/codes/508
    """
    return JSONResponse(
        status_code=508,
        content={"error": "Binding loop detected in collection hierarchy"},
    )


register_example(
    code=508,
    name="Loop Detected",
    path="/codes/508",
    methods=["GET"],
    scenario="WebDAV infinite loop",
)


@router.post("/510")
async def code_510_not_extended(
    x_ext: str | None = Header(default=None, alias="X-EXT-Token"),
):
    """
    510 Not Extended — request must include extension header/token.

    curl -X POST http://127.0.0.1:8000/codes/510
    """
    if not x_ext:
        return JSONResponse(
            status_code=510,
            content={"error": "X-EXT-Token header required for this extension"},
        )
    return {"extension": "ok"}


register_example(
    code=510,
    name="Not Extended",
    path="/codes/510",
    methods=["POST"],
    scenario="Missing required extension header",
)


@router.get("/511")
async def code_511_network_authentication_required():
    """
    511 Network Authentication Required — captive portal / network login (not app auth).

    curl http://127.0.0.1:8000/codes/511
    """
    return JSONResponse(
        status_code=511,
        content={
            "error": "Network login required",
            "portal": "https://wifi.example.com/login",
        },
    )


register_example(
    code=511,
    name="Network Authentication Required",
    path="/codes/511",
    methods=["GET"],
    scenario="Captive portal style network gate",
)
