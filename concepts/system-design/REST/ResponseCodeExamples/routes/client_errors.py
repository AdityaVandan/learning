"""
4xx Client error responses.

Reference: ../ResponseCodes.md § 4xx
"""

from __future__ import annotations

from fastapi import APIRouter, Header, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field, field_validator

from common import (
    DOCUMENT_BODY,
    DOCUMENT_ETAG,
    DOCUMENT_VERSION,
    emails_in_use,
    gone_paths,
    locked_resources,
    register_example,
    resolve_user,
)

router = APIRouter(prefix="/codes", tags=["4xx Client Errors"])


class OrderBody(BaseModel):
    email: str
    quantity: int = Field(ge=1)


class ValidatedSignup(BaseModel):
    email: str
    start_date: str
    end_date: str

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, end_date: str, info):
        start = info.data.get("start_date")
        if start and end_date < start:
            raise ValueError("end_date must be on or after start_date")
        return end_date


# ---------------------------------------------------------------------------
# 400 Bad Request
# ---------------------------------------------------------------------------


@router.post("/400")
async def code_400_bad_request(request: Request):
    """
    400 Bad Request — malformed syntax (invalid JSON, wrong types, missing required fields).

    Compare with 422: 400 = cannot parse/understand request shape.

    curl -X POST http://127.0.0.1:8000/codes/400 -H "Content-Type: application/json" -d 'not-json'
    """
    try:
        await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "Malformed JSON body"},
        )
    return JSONResponse(status_code=400, content={"error": "Unexpected valid JSON for this demo"})


register_example(
    code=400,
    name="Bad Request",
    path="/codes/400",
    methods=["POST"],
    scenario="Invalid JSON body",
)


# ---------------------------------------------------------------------------
# 401 / 403
# ---------------------------------------------------------------------------


@router.get("/401")
async def code_401_unauthorized(
    authorization: str | None = Header(default=None),
):
    """
    401 Unauthorized — missing/invalid authentication (WWW-Authenticate).

    curl http://127.0.0.1:8000/codes/401
    curl http://127.0.0.1:8000/codes/401 -H "Authorization: Bearer wrong"
    """
    user = resolve_user(authorization)
    print(user, authorization)
    if user.role == "guest":
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required"},
            headers={"WWW-Authenticate": 'Bearer realm="learning-api"'},
        )
    return {"message": "Authenticated", "role": user.role}


register_example(
    code=401,
    name="Unauthorized",
    path="/codes/401",
    methods=["GET"],
    scenario="No/invalid Bearer token",
)


@router.get("/402")
async def code_402_payment_required():
    """
    402 Payment Required — reserved; sometimes used for billing/quota.

    curl http://127.0.0.1:8000/codes/402
    """
    return JSONResponse(
        status_code=402,
        content={"error": "Subscription required", "upgrade_url": "/billing"},
    )


register_example(
    code=402,
    name="Payment Required",
    path="/codes/402",
    methods=["GET"],
    scenario="Billing / quota gate",
)


@router.delete("/403/admin-only")
async def code_403_forbidden(authorization: str | None = Header(default=None)):
    """
    403 Forbidden — authenticated but not permitted (vs 401).

    Use: Authorization: Bearer user-token (not admin).

    curl -X DELETE http://127.0.0.1:8000/codes/403/admin-only -H "Authorization: Bearer user-token"
    """
    user = resolve_user(authorization)
    if user.role == "guest":
        return JSONResponse(
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer realm="learning-api"'},
            content={"error": "Login required"},
        )
    if user.role != "admin":
        return JSONResponse(
            status_code=403,
            content={"error": "Admin role required to delete this resource"},
        )
    return {"message": "Deleted (demo)"}


register_example(
    code=403,
    name="Forbidden",
    path="/codes/403/admin-only",
    methods=["DELETE"],
    scenario="Valid user-token but not admin",
)


@router.get("/404/{resource_id}")
async def code_404_not_found(resource_id: str):
    """
    404 Not Found — resource does not exist (or hidden intentionally).

    curl http://127.0.0.1:8000/codes/404/does-not-exist
    """
    return JSONResponse(status_code=404, content={"error": f"Resource '{resource_id}' not found"})


register_example(
    code=404,
    name="Not Found",
    path="/codes/404/{resource_id}",
    methods=["GET"],
    scenario="Unknown resource id",
)


@router.get("/405", response_model=None)
async def code_405_method_not_allowed_get_only():
    """
    405 Method Not Allowed — verb not supported; Allow header lists valid methods.

    curl -X POST http://127.0.0.1:8000/codes/405
    """
    return {"only": "GET is implemented on this path"}


register_example(
    code=405,
    name="Method Not Allowed",
    path="/codes/405",
    methods=["GET"],
    scenario="POST to GET-only route → FastAPI returns 405 + Allow",
)


@router.get("/406")
async def code_406_not_acceptable(
    accept: str | None = Header(default=None),
):
    """
    406 Not Acceptable — cannot satisfy Accept content negotiation.

    curl http://127.0.0.1:8000/codes/406 -H "Accept: application/xml"
    """
    if accept and "application/json" not in accept and "*/*" not in accept:
        return JSONResponse(
            status_code=406,
            content={"error": "Only application/json supported"},
        )
    return {"format": "json"}


register_example(
    code=406,
    name="Not Acceptable",
    path="/codes/406",
    methods=["GET"],
    scenario="Accept: application/xml when only JSON exists",
)


@router.get("/407")
async def code_407_proxy_auth_required():
    """
    407 Proxy Authentication Required — proxy needs credentials (uncommon in app servers).

    curl http://127.0.0.1:8000/codes/407
    """
    return JSONResponse(
        status_code=407,
        headers={"Proxy-Authenticate": 'Basic realm="corporate-proxy"'},
        content={"error": "Proxy authentication required"},
    )


register_example(
    code=407,
    name="Proxy Authentication Required",
    path="/codes/407",
    methods=["GET"],
    scenario="Corporate proxy credential gate",
)


@router.get("/408")
async def code_408_request_timeout():
    """
    408 Request Timeout — server gave up waiting for the client to finish sending.

    curl http://127.0.0.1:8000/codes/408
    """
    return JSONResponse(
        status_code=408,
        content={"error": "Server timed out waiting for complete request"},
    )


register_example(
    code=408,
    name="Request Timeout",
    path="/codes/408",
    methods=["GET"],
    scenario="Incomplete/slow client upload",
)


@router.post("/409/orders")
async def code_409_conflict(body: OrderBody):
    """
    409 Conflict — request conflicts with current state (duplicate unique key, wrong state).

    Try email: taken@example.com

    curl -X POST http://127.0.0.1:8000/codes/409/orders -H "Content-Type: application/json" -d '{"email":"taken@example.com","quantity":1}'
    """
    if body.email in emails_in_use:
        return JSONResponse(
            status_code=409,
            content={"error": "Email already registered", "field": "email"},
        )
    emails_in_use.add(body.email)
    return {"status": "order placed", "email": body.email}


register_example(
    code=409,
    name="Conflict",
    path="/codes/409/orders",
    methods=["POST"],
    scenario="Duplicate unique email",
)


@router.get("/410/gone-resource")
async def code_410_gone():
    """
    410 Gone — resource permanently removed (stronger than 404 for deprecated URLs).

    curl http://127.0.0.1:8000/codes/410/gone-resource
    """
    if "/codes/410/gone-resource" in gone_paths:
        return JSONResponse(
            status_code=410,
            content={"error": "API v1 removed permanently", "successor": "/v2/docs"},
        )
    return {"status": "available"}


register_example(
    code=410,
    name="Gone",
    path="/codes/410/gone-resource",
    methods=["GET"],
    scenario="Deprecated endpoint permanently removed",
)


@router.put("/411")
async def code_411_length_required(
    content_length: str | None = Header(default=None, alias="Content-Length"),
):
    """
    411 Length Required — server requires Content-Length (legacy servers).

    curl -X PUT http://127.0.0.1:8000/codes/411
    """
    if not content_length:
        return JSONResponse(
            status_code=411,
            content={"error": "Content-Length header required for this endpoint"},
        )
    return {"received_bytes": content_length}


register_example(
    code=411,
    name="Length Required",
    path="/codes/411",
    methods=["PUT"],
    scenario="PUT without Content-Length",
)


@router.put("/412/document")
async def code_412_precondition_failed(
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    """
    412 Precondition Failed — If-Match ETag does not match current version (optimistic locking).

    curl -X PUT http://127.0.0.1:8000/codes/412/document -H 'If-Match: "wrong-etag"' -H "Content-Type: application/json" -d '{}'
    """
    if if_match != DOCUMENT_ETAG:
        return JSONResponse(
            status_code=412,
            content={
                "error": "ETag mismatch",
                "current_etag": DOCUMENT_ETAG,
            },
        )
    return {"message": "Update applied", "etag": DOCUMENT_ETAG}


register_example(
    code=412,
    name="Precondition Failed",
    path="/codes/412/document",
    methods=["PUT"],
    scenario="Stale If-Match ETag",
)


@router.post("/413")
async def code_413_content_too_large(request: Request):
    """
    413 Content Too Large — request body exceeds limit (often at gateway).

  Body > 1000 bytes triggers demo limit.

    curl -X POST http://127.0.0.1:8000/codes/413 --data-binary "@large.txt"
    """
    body = await request.body()
    if len(body) > 1000:
        return JSONResponse(
            status_code=413,
            content={"error": "Body exceeds 1000 byte demo limit"},
        )
    return {"bytes_received": len(body)}


register_example(
    code=413,
    name="Content Too Large",
    path="/codes/413",
    methods=["POST"],
    scenario="Upload larger than 1000 bytes",
)


@router.get("/414/{long_segment:path}")
async def code_414_uri_too_long(long_segment: str):
    """
    414 URI Too Long — path/query exceeds server limit.

    curl "http://127.0.0.1:8000/codes/414/$(python3 -c 'print(\"a\"*8000)')"
    """
    if len(long_segment) > 2048:
        return JSONResponse(status_code=414, content={"error": "URI segment too long"})
    return {"segment_length": len(long_segment)}


register_example(
    code=414,
    name="URI Too Long",
    path="/codes/414/{long_segment}",
    methods=["GET"],
    scenario="Path segment longer than 2048 chars",
)


@router.post("/415")
async def code_415_unsupported_media_type(request: Request):
    """
    415 Unsupported Media Type — wrong Content-Type for this endpoint.

    curl -X POST http://127.0.0.1:8000/codes/415 -H "Content-Type: text/plain" -d hello
    """
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("application/json"):
        return JSONResponse(
            status_code=415,
            content={"error": "Expected Content-Type: application/json"},
        )
    return await request.json()


register_example(
    code=415,
    name="Unsupported Media Type",
    path="/codes/415",
    methods=["POST"],
    scenario="text/plain instead of application/json",
)


@router.get("/416/range-test")
async def code_416_range_not_satisfiable(
    range_header: str | None = Header(default=None, alias="Range"),
):
    """
    416 Range Not Satisfiable — Range header outside file bounds.

    curl http://127.0.0.1:8000/codes/416/range-test -H "Range: bytes=99999-100000"
    """
    total = len(DOCUMENT_BODY)
    if range_header:
        return JSONResponse(
            status_code=416,
            headers={"Content-Range": f"bytes */{total}"},
            content={"error": "Range outside document size"},
        )
    return PlainTextResponse(DOCUMENT_BODY.decode())


register_example(
    code=416,
    name="Range Not Satisfiable",
    path="/codes/416/range-test",
    methods=["GET"],
    scenario="Range bytes beyond file end",
)


@router.post("/417")
async def code_417_expectation_failed(
    expect: str | None = Header(default=None, alias="Expect"),
):
    """
    417 Expectation Failed — server cannot meet Expect header requirements.

    curl -X POST http://127.0.0.1:8000/codes/417 -H "Expect: custom-magic"
    """
    if expect and expect.lower() != "100-continue":
        return JSONResponse(
            status_code=417,
            content={"error": f"Cannot satisfy Expect: {expect}"},
        )
    return {"message": "Expect header acceptable or absent"}


register_example(
    code=417,
    name="Expectation Failed",
    path="/codes/417",
    methods=["POST"],
    scenario="Unsupported Expect header value",
)


@router.get("/418")
async def code_418_im_a_teapot():
    """
    418 I'm a teapot — RFC 2324 joke status (do not use in production APIs).

    curl http://127.0.0.1:8000/codes/418
    """
    return JSONResponse(
        status_code=418,
        content={"error": "I am a teapot", "short_and_stout": True},
    )


register_example(
    code=418,
    name="I'm a teapot",
    path="/codes/418",
    methods=["GET"],
    scenario="Easter egg / non-standard demo",
)


@router.get("/421")
async def code_421_misdirected_request():
    """
    421 Misdirected Request — request routed to wrong origin (HTTP/2 connection reuse).

    curl http://127.0.0.1:8000/codes/421
    """
    return JSONResponse(
        status_code=421,
        content={"error": "Request sent to wrong host for this certificate/SNI"},
    )


register_example(
    code=421,
    name="Misdirected Request",
    path="/codes/421",
    methods=["GET"],
    scenario="HTTP/2 wrong authority routing",
)


@router.post("/422")
async def code_422_unprocessable_content(body: ValidatedSignup):
    """
    422 Unprocessable Content — valid JSON but business rules fail (field validation).

    curl -X POST http://127.0.0.1:8000/codes/422 -H "Content-Type: application/json" -d '{"email":"a@b.com","start_date":"2026-06-01","end_date":"2026-01-01"}'
    """
    return {"status": "signup ok", "email": body.email}


register_example(
    code=422,
    name="Unprocessable Content",
    path="/codes/422",
    methods=["POST"],
    scenario="end_date before start_date → validation error",
)


@router.put("/423/{resource_id}")
async def code_423_locked(resource_id: str):
    """
    423 Locked — resource locked for exclusive operation (WebDAV-style).

    First call locks; second returns 423.

    curl -X PUT http://127.0.0.1:8000/codes/423/report -d ''
    """
    key = f"lock:{resource_id}"
    if key in locked_resources:
        return JSONResponse(
            status_code=423,
            content={"error": "Resource locked by another operation"},
        )
    locked_resources.add(key)
    return {"message": f"Locked {resource_id} (demo). Restart server to clear."}


register_example(
    code=423,
    name="Locked",
    path="/codes/423/{resource_id}",
    methods=["PUT"],
    scenario="Second PUT while resource locked",
)


@router.post("/424")
async def code_424_failed_dependency():
    """
    424 Failed Dependency — action failed because a prior step in a batch failed.

    curl -X POST http://127.0.0.1:8000/codes/424
    """
    return JSONResponse(
        status_code=424,
        content={
            "error": "Cannot publish: dependency 'upload-asset' failed",
            "failed_step": "upload-asset",
        },
    )


register_example(
    code=424,
    name="Failed Dependency",
    path="/codes/424",
    methods=["POST"],
    scenario="Batch step depends on failed prior step",
)


@router.post("/425")
async def code_425_too_early():
    """
    425 Too Early — server rejects replay-risky request (TLS 0-RTT early data).

    curl -X POST http://127.0.0.1:8000/codes/425
    """
    return JSONResponse(
        status_code=425,
        content={"error": "Request may be replayed; retry without early data"},
    )


register_example(
    code=425,
    name="Too Early",
    path="/codes/425",
    methods=["POST"],
    scenario="Anti-replay / TLS early data",
)


@router.get("/426")
async def code_426_upgrade_required():
    """
    426 Upgrade Required — client must use TLS or newer protocol.

    curl http://127.0.0.1:8000/codes/426
    """
    return JSONResponse(
        status_code=426,
        headers={"Upgrade": "TLS/1.3"},
        content={"error": "HTTPS required"},
    )


register_example(
    code=426,
    name="Upgrade Required",
    path="/codes/426",
    methods=["GET"],
    scenario="Force HTTPS / protocol upgrade",
)


@router.put("/428/document")
async def code_428_precondition_required(
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    """
    428 Precondition Required — server requires If-Match/ETag on mutating requests.

    curl -X PUT http://127.0.0.1:8000/codes/428/document -H "Content-Type: application/json" -d '{}'
    """
    if not if_match:
        return JSONResponse(
            status_code=428,
            content={
                "error": "If-Match header required",
                "current_etag": DOCUMENT_ETAG,
            },
        )
    return {"updated": True, "version": DOCUMENT_VERSION}


register_example(
    code=428,
    name="Precondition Required",
    path="/codes/428/document",
    methods=["PUT"],
    scenario="PUT without If-Match",
)


@router.get("/429")
async def code_429_too_many_requests(request: Request):
    """
    429 Too Many Requests — rate limit exceeded; Retry-After tells clients when to retry.

    Hit this endpoint >5 times in 10 seconds.

    curl http://127.0.0.1:8000/codes/429
    """
    from common import check_rate_limit

    client_key = request.client.host if request.client else "local"
    allowed, retry_after = check_rate_limit(client_key)
    if not allowed:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(retry_after)},
            content={"error": "Rate limit exceeded", "retry_after_seconds": retry_after},
        )
    return {"remaining_bucket": "ok"}


register_example(
    code=429,
    name="Too Many Requests",
    path="/codes/429",
    methods=["GET"],
    scenario=">5 requests in 10s from same IP",
)


@router.get("/431")
async def code_431_header_fields_too_large(
    x_demo_big: str | None = Header(default=None, alias="X-Demo-Big"),
):
    """
    431 Request Header Fields Too Large — headers exceed limit (cookies, auth tokens).

    curl http://127.0.0.1:8000/codes/431 -H "X-Demo-Big: $(python3 -c 'print(\"x\"*9000)')"
    """
    if x_demo_big and len(x_demo_big) > 8192:
        return JSONResponse(
            status_code=431,
            content={"error": "Header X-Demo-Big exceeds demo limit"},
        )
    return {
        "hint": "Send X-Demo-Big header >8192 chars to trigger 431",
        "received_length": len(x_demo_big or ""),
    }


register_example(
    code=431,
    name="Request Header Fields Too Large",
    path="/codes/431",
    methods=["GET"],
    scenario="Oversized X-Demo-Big header",
)


@router.get("/451/{region}")
async def code_451_unavailable_for_legal_reasons(region: str):
    """
    451 Unavailable For Legal Reasons — blocked by law (geo restriction, takedown).

    curl http://127.0.0.1:8000/codes/451/XX
    """
    blocked = {"XX", "YY"}
    if region.upper() in blocked:
        return JSONResponse(
            status_code=451,
            headers={"Link": '<https://example.com/legal>; rel="blocked-by"'},
            content={"error": "Content unavailable in this region"},
        )
    return {"region": region, "allowed": True}


register_example(
    code=451,
    name="Unavailable For Legal Reasons",
    path="/codes/451/{region}",
    methods=["GET"],
    scenario="Region XX or YY blocked",
)
