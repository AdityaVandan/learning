"""
3xx Redirection responses.

Reference: ../ResponseCodes.md § 3xx
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Header, Response
from fastapi.responses import JSONResponse, RedirectResponse

from common import DOCUMENT_ETAG, register_example

router = APIRouter(prefix="/codes", tags=["3xx Redirection"])


@router.get("/300")
async def code_300_multiple_choices():
    """
    300 Multiple Choices — server offers multiple representations; client picks one.

    curl http://127.0.0.1:8000/codes/300
    """
    return JSONResponse(
        status_code=300,
        content={
            "choices": [
                {"href": "/codes/200", "type": "application/json"},
                {"href": "/codes/206/document", "type": "text/plain"},
            ],
        },
    )


register_example(
    code=300,
    name="Multiple Choices",
    path="/codes/300",
    methods=["GET"],
    scenario="Multiple representations available",
)


@router.get("/301")
async def code_301_moved_permanently():
    """
    301 Moved Permanently — resource permanently at a new URL (cacheable redirect).

    curl -i http://127.0.0.1:8000/codes/301
    """
    return RedirectResponse(url="/codes/200", status_code=301)


register_example(
    code=301,
    name="Moved Permanently",
    path="/codes/301",
    methods=["GET"],
    scenario="Permanent redirect to /codes/200",
)


@router.get("/302")
async def code_302_found():
    """
    302 Found — temporary redirect; many clients historically changed POST→GET.

    curl -i http://127.0.0.1:8000/codes/302
    """
    return RedirectResponse(url="/codes/200", status_code=302)


register_example(
    code=302,
    name="Found",
    path="/codes/302",
    methods=["GET"],
    scenario="Temporary redirect (method may change to GET)",
)


@router.post("/303")
async def code_303_see_other():
    """
    303 See Other — after POST, redirect client to GET a result/status page.

    Real scenario: form POST → redirect to GET /orders/123/status.

    curl -i -X POST http://127.0.0.1:8000/codes/303
    """
    return RedirectResponse(url="/codes/200", status_code=303)


register_example(
    code=303,
    name="See Other",
    path="/codes/303",
    methods=["POST"],
    scenario="POST then redirect to GET result URL",
)


@router.get("/304/document")
async def code_304_not_modified(
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    if_modified_since: str | None = Header(default=None, alias="If-Modified-Since"),
):
    """
    304 Not Modified — conditional GET: cached copy is still valid (no body).

    Send If-None-Match: "doc-v1" OR If-Modified-Since with a recent date.

    curl http://127.0.0.1:8000/codes/304/document -H 'If-None-Match: "doc-v1"'
    """
    last_modified = "Wed, 01 Jan 2025 00:00:00 GMT"

    etag_match = if_none_match == DOCUMENT_ETAG
    date_match = False
    if if_modified_since:
        try:
            client_dt = datetime.strptime(
                if_modified_since, "%a, %d %b %Y %H:%M:%S GMT"
            ).replace(tzinfo=timezone.utc)
            server_dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
            date_match = client_dt >= server_dt
        except ValueError:
            date_match = False

    if etag_match or date_match:
        return Response(
            status_code=304,
            headers={"ETag": DOCUMENT_ETAG, "Last-Modified": last_modified},
        )

    return Response(
        content=b'{"id":1,"title":"Learning doc"}',
        media_type="application/json",
        headers={"ETag": DOCUMENT_ETAG, "Last-Modified": last_modified},
    )


register_example(
    code=304,
    name="Not Modified",
    path="/codes/304/document",
    methods=["GET"],
    scenario="If-None-Match matches ETag → empty 304",
)


@router.put("/307")
async def code_307_temporary_redirect():
    """
    307 Temporary Redirect — temporary move; HTTP method must stay the same (unlike many 302 clients).

    curl -i -X PUT http://127.0.0.1:8000/codes/307
    """
    return RedirectResponse(url="/codes/200", status_code=307)


register_example(
    code=307,
    name="Temporary Redirect",
    path="/codes/307",
    methods=["PUT"],
    scenario="Temporary redirect preserving method",
)


@router.delete("/308")
async def code_308_permanent_redirect():
    """
    308 Permanent Redirect — permanent move; method preserved.

    curl -i -X DELETE http://127.0.0.1:8000/codes/308
    """
    return RedirectResponse(url="/codes/204", status_code=308)


register_example(
    code=308,
    name="Permanent Redirect",
    path="/codes/308",
    methods=["DELETE"],
    scenario="Permanent redirect preserving method",
)
