"""
DELETE examples: remove a resource (idempotent).
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from common import delete_item, register_example

router = APIRouter(prefix="/verbs", tags=["DELETE"])


@router.delete("/delete/items/{item_id}")
async def delete_item_route(item_id: str):
    """
    DELETE removes a resource.
    Typically idempotent: deleting an already-deleted resource results in the same end state.

    Here we return 204 if it existed; 404 if it never existed.
    Some APIs return 204 even if already deleted — both styles exist.
    """

    existed = delete_item(item_id)
    if not existed:
        return JSONResponse(status_code=404, content={"error": "Item not found"})
    return Response(status_code=204)


register_example(
    verb="DELETE",
    name="Delete item",
    path="/verbs/delete/items/{item_id}",
    methods=["DELETE"],
    semantics=["not safe", "idempotent"],
    scenario="Remove a resource; repeat calls keep resource absent",
)

