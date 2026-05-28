"""
HTTP request-verb learning API (FastAPI).

Each route under /verbs/* demonstrates typical usage patterns and semantics
for REST verbs (safety, idempotency, partial updates, discovery).

Run (from repo root):
  source learningenv/bin/activate
  pip install -r concepts/system-design/REST/RequestVerbExamples/requirements.txt
  cd concepts/system-design/REST/RequestVerbExamples
  uvicorn main:app --reload --host 127.0.0.1 --port 8001
"""

from fastapi import FastAPI

from common import VERB_REGISTRY
from routes import delete, get, head_options, patch, post, put, trace_connect

app = FastAPI(
    title="REST Request Verb Examples",
    description=(
        "Runnable examples for REST request verbs (GET, POST, PUT, PATCH, DELETE, "
        "HEAD, OPTIONS, TRACE, CONNECT). Each endpoint explains the typical "
        "semantics and includes realistic request/response behavior."
    ),
    version="1.0.0",
)

# Import order matters: route modules call register_example() at import time.
app.include_router(get.router)
app.include_router(post.router)
app.include_router(put.router)
app.include_router(patch.router)
app.include_router(delete.router)
app.include_router(head_options.router)
app.include_router(trace_connect.router)


@app.get("/")
async def index():
    sorted_registry = sorted(VERB_REGISTRY, key=lambda x: (x["verb"], x["path"]))
    return {
        "message": "HTTP request verb learning API",
        "docs": "/docs",
        "count": len(sorted_registry),
        "examples": sorted_registry,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}

