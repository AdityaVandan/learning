"""
PUT examples: full replacement of a resource (idempotent).
"""

from __future__ import annotations

from fastapi import APIRouter, Header, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from common import item_etags, items, register_example, replace_item

router = APIRouter(prefix="/verbs", tags=["PUT"])


class PutItemBody(BaseModel):
    name: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


@router.put("/put/items/{item_id}")
async def put_replace_item(
    item_id: str,
    body: PutItemBody,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    """
    PUT replaces the full representation at a known URL.
    Typically idempotent: repeating the same PUT yields the same end state.

    Also demonstrates optimistic concurrency: If-Match must match the latest ETag.
    """

    current_etag = item_etags.get(item_id)
    if current_etag and if_match and if_match != current_etag:
        return JSONResponse(
            status_code=412,
            content={"error": "ETag mismatch", "current_etag": current_etag},
        )

    existed = item_id in items
    item = replace_item(item_id=item_id, name=body.name, tags=body.tags)
    etag = item_etags.get(item_id) or ""
    response.headers["ETag"] = etag
    if not existed:
        response.status_code = 201
        response.headers["Location"] = f"/verbs/get/items/{item_id}"
    return {"item": item, "existed": existed}


register_example(
    verb="PUT",
    name="Replace item (upsert, idempotent)",
    path="/verbs/put/items/{item_id}",
    methods=["PUT"],
    semantics=["not safe", "idempotent", "full replacement"],
    scenario="Replace the entire resource; may create if absent (201) or update (200)",
)

