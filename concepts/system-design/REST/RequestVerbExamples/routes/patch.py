"""
PATCH examples: partial update (usually idempotent in RESTful designs, but not guaranteed).
"""

from __future__ import annotations

from fastapi import APIRouter, Header, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from common import item_etags, items, patch_item, register_example

router = APIRouter(prefix="/verbs", tags=["PATCH"])


class PatchItemBody(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None


@router.patch("/patch/items/{item_id}")
async def patch_update_item(
    item_id: str,
    body: PatchItemBody,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    """
    PATCH partially updates fields on a resource.
    Uses If-Match to avoid lost updates, similar to PUT.
    """

    if item_id not in items:
        return JSONResponse(status_code=404, content={"error": "Item not found"})

    current_etag = item_etags.get(item_id)
    if current_etag and if_match and if_match != current_etag:
        return JSONResponse(
            status_code=412,
            content={"error": "ETag mismatch", "current_etag": current_etag},
        )

    updated = patch_item(item_id=item_id, name=body.name, tags=body.tags)
    etag = item_etags.get(item_id) or ""
    response.headers["ETag"] = etag
    return {"item": updated}


register_example(
    verb="PATCH",
    name="Partial update item",
    path="/verbs/patch/items/{item_id}",
    methods=["PATCH"],
    semantics=["not safe", "partial update", "idempotent (common, but depends on patch)"],
    scenario="Update only the fields provided (e.g., name), leaving others unchanged",
)

