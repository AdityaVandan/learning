"""
2xx Success responses.

Reference: ../ResponseCodes.md § 2xx
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Header, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from common import (
    DOCUMENT_BODY,
    DOCUMENT_ETAG,
    created_items,
    jobs,
    register_example,
)

router = APIRouter(prefix="/codes", tags=["2xx Success"])


class CreateItemBody(BaseModel):
    name: str = Field(min_length=1)


class SignupBody(BaseModel):
    email: str
    start_date: str
    end_date: str


@router.get("/200")
async def code_200_ok():
    """
    200 OK — standard successful GET/operation with a response body.

    curl http://127.0.0.1:8000/codes/200
    """
    return {"message": "Request succeeded.", "data": {"id": 1, "name": "example"}}


register_example(
    code=200, name="OK", path="/codes/200", methods=["GET"], scenario="Successful read"
)


@router.post("/201", status_code=201)
async def code_201_created(body: CreateItemBody, response: Response):
    """
    201 Created — a new resource was persisted; include Location + representation.

    Real scenario: POST /users returns 201 and Location: /users/{id}.

    curl -X POST http://127.0.0.1:8000/codes/201 -H "Content-Type: application/json" -d '{"name":"widget"}'
    """
    item_id = str(uuid.uuid4())[:8]
    created_items[item_id] = {"id": item_id, "name": body.name}
    location = f"/codes/201/items/{item_id}"
    response.headers["Location"] = location
    return {"id": item_id, "name": body.name, "location": location}


register_example(
    code=201,
    name="Created",
    path="/codes/201",
    methods=["POST"],
    scenario="POST creates resource; Location header set",
)


@router.get("/201/items/{item_id}")
async def get_created_item(item_id: str):
    item = created_items.get(item_id)
    if not item:
        return JSONResponse(status_code=404, content={"error": "Item not found"})
    return item


@router.post("/202")
async def code_202_accepted():
    """
    202 Accepted — async processing started; body may include job id / status URL.

    curl -X POST http://127.0.0.1:8000/codes/202
    """
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "pending", "progress": 0}
    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status_url": f"/codes/202/jobs/{job_id}",
            "message": "Export started; poll status_url.",
        },
    )


@router.get("/202/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = jobs.get(job_id, {"status": "unknown"})
    return job


register_example(
    code=202,
    name="Accepted",
    path="/codes/202",
    methods=["POST"],
    scenario="Async job accepted; poll /codes/202/jobs/{id}",
)


@router.get("/203")
async def code_203_non_authoritative(response: Response):
    """
    203 Non-Authoritative Information — transforming proxy altered the response.

    curl http://127.0.0.1:8000/codes/203
    """
    response.headers["Warning"] = '110 - "Response transformed by demo proxy"'
    return {"message": "Data may have been modified by an intermediary."}


register_example(
    code=203,
    name="Non-Authoritative Information",
    path="/codes/203",
    methods=["GET"],
    scenario="Warning header indicates transformed response",
)


@router.delete("/204")
async def code_204_no_content():
    """
    204 No Content — success with intentionally empty body (common on DELETE).

    curl -X DELETE http://127.0.0.1:8000/codes/204 -i
    """
    return Response(status_code=204)


register_example(
    code=204,
    name="No Content",
    path="/codes/204",
    methods=["DELETE"],
    scenario="Successful delete with no response body",
)


@router.post("/205")
async def code_205_reset_content():
    """
    205 Reset Content — tells the client to reset document/view state (legacy HTML flows).

    curl -X POST http://127.0.0.1:8000/codes/205
    """
    return Response(status_code=205, content=b"")


register_example(
    code=205,
    name="Reset Content",
    path="/codes/205",
    methods=["POST"],
    scenario="Client should reset UI state",
)


@router.get("/206/document")
async def code_206_partial_content(
    request: Request,
    range_header: str | None = Header(default=None, alias="Range"),
):
    """
    206 Partial Content — honor Range for downloads/streaming.

    Send: Range: bytes=0-4

    curl http://127.0.0.1:8000/codes/206/document -H "Range: bytes=0-9"
    """
    total = len(DOCUMENT_BODY)
    if not range_header or not range_header.startswith("bytes="):
        return PlainTextResponse(DOCUMENT_BODY.decode(), media_type="text/plain")

    spec = range_header.removeprefix("bytes=").strip()
    if "-" not in spec:
        return JSONResponse(
            status_code=416,
            headers={"Content-Range": f"bytes */{total}"},
            content={"error": "Invalid Range"},
        )

    start_s, _, end_s = spec.partition("-")
    try:
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else total - 1
    except ValueError:
        return JSONResponse(
            status_code=416,
            headers={"Content-Range": f"bytes */{total}"},
            content={"error": "Invalid Range"},
        )

    if start >= total or end >= total or start > end:
        return JSONResponse(
            status_code=416,
            headers={"Content-Range": f"bytes */{total}"},
            content={"error": "Range not satisfiable"},
        )

    chunk = DOCUMENT_BODY[start : end + 1]
    return Response(
        status_code=206,
        content=chunk,
        media_type="text/plain",
        headers={
            "Content-Range": f"bytes {start}-{end}/{total}",
            "Accept-Ranges": "bytes",
        },
    )


register_example(
    code=206,
    name="Partial Content",
    path="/codes/206/document",
    methods=["GET"],
    scenario="Range: bytes=0-N returns slice with Content-Range",
)


@router.post("/207")
async def code_207_multi_status():
    """
    207 Multi-Status — batch/WebDAV operations with per-item status (rare in REST).

    curl -X POST http://127.0.0.1:8000/codes/207 -H "Content-Type: application/json" -d '{"ops":[{"id":1},{"id":2}]}'
    """
    return JSONResponse(
        status_code=207,
        content={
            "responses": [
                {"href": "/items/1", "status": 201},
                {"href": "/items/2", "status": 409, "detail": "duplicate"},
            ],
        },
    )


register_example(
    code=207,
    name="Multi-Status",
    path="/codes/207",
    methods=["POST"],
    scenario="Batch response with per-item HTTP status",
)


@router.get("/208")
async def code_208_already_reported():
    """
    208 Already Reported — WebDAV: member listed in an earlier response part.

    curl http://127.0.0.1:8000/codes/208
    """
    return JSONResponse(
        status_code=208,
        content={"message": "DAV:members already enumerated in a previous multistatus part."},
    )


register_example(
    code=208,
    name="Already Reported",
    path="/codes/208",
    methods=["GET"],
    scenario="WebDAV collection enumeration",
)


@router.get("/226")
async def code_226_im_used(response: Response):
    """
    226 IM Used — delta encoding applied to a prior representation (rare).

    curl http://127.0.0.1:8000/codes/226
    """
    response.headers["IM"] = "delta"
    return {"message": "Instance manipulation (delta) applied to cached representation."}


register_example(
    code=226,
    name="IM Used",
    path="/codes/226",
    methods=["GET"],
    scenario="Delta encoding against prior representation",
)
