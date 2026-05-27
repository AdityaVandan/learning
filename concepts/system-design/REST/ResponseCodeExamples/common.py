"""
Shared state and helpers for HTTP status-code demos.

See ../ResponseCodes.md for definitions of each code.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

# Populated by route modules at import time for GET /
CODE_REGISTRY: list[dict[str, Any]] = []


def register_example(
    *,
    code: int,
    name: str,
    path: str,
    methods: list[str],
    scenario: str,
) -> None:
    CODE_REGISTRY.append(
        {
            "code": code,
            "name": name,
            "path": path,
            "methods": methods,
            "scenario": scenario,
        }
    )


# --- In-memory "database" for realistic demos ---

DOCUMENT_ETAG = '"doc-v1"'
DOCUMENT_BODY = b"Hello, this is a downloadable document for Range/ETag demos."
DOCUMENT_VERSION = 1

jobs: dict[str, dict[str, Any]] = {}
created_items: dict[str, dict[str, Any]] = {}
gone_paths: set[str] = {"/codes/410/gone-resource"}
locked_resources: set[str] = set()
emails_in_use: set[str] = {"taken@example.com"}

# Rate limit: 5 requests per 10 seconds per client key (IP from X-Forwarded-For or "local")
_rate_buckets: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW_SEC = 10

maintenance_mode = False


@dataclass
class UserContext:
    token: str | None
    role: str  # "guest" | "user" | "admin"


def parse_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def resolve_user(authorization: str | None) -> UserContext:
    """
    Demo tokens (send as: Authorization: Bearer <token>):
      - user-token   -> role user
      - admin-token  -> role admin
    """
    token = parse_bearer(authorization)
    if token == "admin-token":
        return UserContext(token=token, role="admin")
    if token == "user-token":
        return UserContext(token=token, role="user")
    return UserContext(token=token, role="guest")


def check_rate_limit(client_key: str) -> tuple[bool, int]:
    """Returns (allowed, retry_after_seconds)."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SEC
    hits = [t for t in _rate_buckets[client_key] if t > window_start]
    _rate_buckets[client_key] = hits
    if len(hits) >= RATE_LIMIT_MAX:
        oldest = min(hits)
        retry_after = max(1, int(RATE_LIMIT_WINDOW_SEC - (now - oldest)) + 1)
        return False, retry_after
    hits.append(now)
    _rate_buckets[client_key] = hits
    return True, 0
