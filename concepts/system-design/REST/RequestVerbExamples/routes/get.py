"""
GET examples: safe + idempotent reads.
"""

from __future__ import annotations

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from common import item_etags, items, register_example

router = APIRouter(prefix="/verbs", tags=["GET"])


@router.get("/get/items")
async def list_items():
    """
    GET collection: safe + idempotent.

    Typical REST usage: fetch a list. Repeating this request should not change server state.
    """

    return {"count": len(items), "items": list(items.values())}


register_example(
    verb="GET",
    name="List items (collection)",
    path="/verbs/get/items",
    methods=["GET"],
    semantics=["safe", "idempotent", "cacheable (often)"],
    scenario="Read a collection resource",
)


@router.get("/get/items/{item_id}")
async def get_item(item_id: str, if_none_match: str | None = Header(default=None, alias="If-None-Match")):
    """
    GET resource with conditional caching (ETag + If-None-Match).
    """

    item = items.get(item_id)
    if not item:
        return JSONResponse(status_code=404, content={"error": "Item not found"})

    etag = item_etags.get(item_id)
    if etag and if_none_match == etag:
        return JSONResponse(status_code=304, content=None, headers={"ETag": etag})

    return JSONResponse(status_code=200, content=item, headers={"ETag": etag or ""})


register_example(
    verb="GET",
    name="Get item (with ETag)",
    path="/verbs/get/items/{item_id}",
    methods=["GET"],
    semantics=["safe", "idempotent", "cacheable (ETag/304)"],
    scenario="Read a single resource; return 304 when If-None-Match matches",
)

