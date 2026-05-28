"""
HEAD / OPTIONS examples: metadata + discovery.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from common import register_example

router = APIRouter(prefix="/verbs", tags=["HEAD & OPTIONS"])


@router.head("/head/items")
async def head_items(response: Response):
    """
    HEAD returns headers only (no body).
    Useful for checking existence/metadata/caching without downloading the body.
    """

    response.headers["X-Example"] = "head-items"
    return Response(status_code=200)


register_example(
    verb="HEAD",
    name="HEAD items (headers only)",
    path="/verbs/head/items",
    methods=["HEAD"],
    semantics=["safe", "idempotent", "no response body"],
    scenario="Fetch metadata/headers for a resource or collection",
)


@router.options("/options/any")
async def options_any(request: Request, response: Response):
    """
    OPTIONS asks what communication options are available.
    Often used for discovery or preflight (CORS is a special case handled by middleware).
    """

    allow = "GET,POST,PUT,PATCH,DELETE,HEAD,OPTIONS,TRACE,CONNECT"
    response.headers["Allow"] = allow
    return {"allow": allow, "path": str(request.url.path)}


register_example(
    verb="OPTIONS",
    name="OPTIONS discovery (Allow header)",
    path="/verbs/options/any",
    methods=["OPTIONS"],
    semantics=["safe", "idempotent", "capabilities discovery"],
    scenario="Return supported methods via Allow header",
)

