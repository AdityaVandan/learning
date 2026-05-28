"""
POST examples: create sub-resources or trigger non-idempotent actions.
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from common import create_item, non_idempotent_counter, register_example

router = APIRouter(prefix="/verbs", tags=["POST"])


class CreateItemBody(BaseModel):
    name: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


@router.post("/post/items", status_code=201)
async def create_item_post(body: CreateItemBody, response: Response):
    """
    POST to a collection to create a new resource.
    Not guaranteed idempotent: repeating can create multiple resources.
    """

    item = create_item(name=body.name, tags=body.tags)
    location = f"/verbs/get/items/{item['id']}"
    response.headers["Location"] = location
    return {"item": item, "location": location}


register_example(
    verb="POST",
    name="Create item",
    path="/verbs/post/items",
    methods=["POST"],
    semantics=["not safe", "not necessarily idempotent"],
    scenario="Create a new resource under a collection; returns 201 + Location",
)


@router.post("/post/actions/increment")
async def non_idempotent_action():
    """
    POST as an action endpoint (RPC-ish) when you can't model it as a resource update.
    Demonstrates non-idempotency: repeating increments again.
    """

    non_idempotent_counter["value"] += 1
    return {"counter": non_idempotent_counter["value"]}


register_example(
    verb="POST",
    name="Non-idempotent action",
    path="/verbs/post/actions/increment",
    methods=["POST"],
    semantics=["not safe", "not idempotent"],
    scenario="Trigger an action; each call changes state again",
)

