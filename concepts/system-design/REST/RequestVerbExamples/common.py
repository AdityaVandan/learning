"""
Shared state and helpers for HTTP request-verb demos.

This module intentionally keeps state in-memory to demonstrate REST semantics
like safety and idempotency across repeated calls.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any


# Populated by route modules at import time for GET /
VERB_REGISTRY: list[dict[str, Any]] = []


def register_example(
    *,
    verb: str,
    name: str,
    path: str,
    methods: list[str],
    semantics: list[str],
    scenario: str,
) -> None:
    VERB_REGISTRY.append(
        {
            "verb": verb,
            "name": name,
            "path": path,
            "methods": methods,
            "semantics": semantics,
            "scenario": scenario,
        }
    )


# --- In-memory state for realistic demos ---

items: dict[str, dict[str, Any]] = {}
item_etags: dict[str, str] = {}


def _new_etag() -> str:
    return f"\"v-{uuid.uuid4().hex[:8]}\""


def create_item(*, name: str, tags: list[str] | None = None) -> dict[str, Any]:
    item_id = uuid.uuid4().hex[:8]
    now = int(time.time())
    item = {"id": item_id, "name": name, "tags": tags or [], "created_at": now}
    items[item_id] = item
    item_etags[item_id] = _new_etag()
    return item


def replace_item(*, item_id: str, name: str, tags: list[str]) -> dict[str, Any]:
    now = int(time.time())
    item = {"id": item_id, "name": name, "tags": tags, "updated_at": now}
    items[item_id] = item
    item_etags[item_id] = _new_etag()
    return item


def patch_item(*, item_id: str, name: str | None, tags: list[str] | None) -> dict[str, Any]:
    existing = items.get(item_id) or {"id": item_id, "name": "", "tags": []}
    if name is not None:
        existing["name"] = name
    if tags is not None:
        existing["tags"] = tags
    existing["updated_at"] = int(time.time())
    items[item_id] = existing
    item_etags[item_id] = _new_etag()
    return existing


def delete_item(item_id: str) -> bool:
    existed = item_id in items
    items.pop(item_id, None)
    item_etags.pop(item_id, None)
    return existed


@dataclass(frozen=True)
class NonIdempotentCounter:
    """
    Used to demonstrate that POST is not guaranteed to be idempotent.
    Each successful call increments the counter.
    """

    value: int = 0


non_idempotent_counter = {"value": 0}
