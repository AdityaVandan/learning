"""
HTTP status-code learning API (FastAPI).

Each route under /codes/* demonstrates one status code with a realistic REST scenario.
Read route docstrings in routes/*.py and ../ResponseCodes.md for theory.

Run (from repo root):
  source learningenv/bin/activate
  pip install -r concepts/system-design/REST/ResponseCodeExamples/requirements.txt
  cd concepts/system-design/REST/ResponseCodeExamples
  uvicorn main:app --reload --host 127.0.0.1 --port 8000

Interactive docs: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from common import CODE_REGISTRY
from routes import client_errors, informational, redirection, server_errors, success

app = FastAPI(
    title="REST Response Code Examples",
    description=(
        "Runnable examples for HTTP status codes listed in ResponseCodes.md. "
        "Open any route in routes/ to read when/why each code is used."
    ),
    version="1.0.0",
)

# Import order matters: route modules call register_example() at import time.
app.include_router(informational.router)
app.include_router(success.router)
app.include_router(redirection.router)
app.include_router(client_errors.router)
app.include_router(server_errors.router)


@app.get("/")
async def index():
    """
    Discovery index: all implemented status-code demos.

    curl http://127.0.0.1:8000/
    """
    sorted_registry = sorted(CODE_REGISTRY, key=lambda x: x["code"])
    return {
        "message": "HTTP status code learning API",
        "reference": "../ResponseCodes.md",
        "docs": "/docs",
        "count": len(sorted_registry),
        "examples": sorted_registry,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
