# REST Response Code Examples (FastAPI)

Runnable API that returns **every status code** documented in [`../ResponseCodes.md`](../ResponseCodes.md), each with a realistic scenario. Read the route docstrings in `routes/*.py` for learning notes and inline `curl` hints.

## Setup (`learningenv`)

Use the repo-root virtualenv — do **not** create a local `venv` here.

```bash
# from repository root (learning/)
source learningenv/bin/activate
pip install -r concepts/system-design/REST/ResponseCodeExamples/requirements.txt
```

## Run

```bash
source learningenv/bin/activate
cd concepts/system-design/REST/ResponseCodeExamples
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

- Index of all demos: http://127.0.0.1:8000/
- Swagger UI: http://127.0.0.1:8000/docs

## Demo tokens (401 / 403)

| Token | Role |
|-------|------|
| `user-token` | user |
| `admin-token` | admin |

```bash
curl http://127.0.0.1:8000/codes/401 -H "Authorization: Bearer user-token"
curl -X DELETE http://127.0.0.1:8000/codes/403/admin-only -H "Authorization: Bearer user-token"
```

## Key `curl` recipes

### Caching — 304 Not Modified

```bash
# First fetch (200 + ETag)
curl -i http://127.0.0.1:8000/codes/304/document

# Conditional request (304, empty body)
curl -i http://127.0.0.1:8000/codes/304/document -H 'If-None-Match: "doc-v1"'
```

### Partial content — 206 / 416

```bash
curl -i http://127.0.0.1:8000/codes/206/document -H "Range: bytes=0-9"
curl -i http://127.0.0.1:8000/codes/416/range-test -H "Range: bytes=99999-100000"
```

### Optimistic locking — 412 / 428

```bash
# 428: missing If-Match
curl -i -X PUT http://127.0.0.1:8000/codes/428/document -H "Content-Type: application/json" -d '{}'

# 412: wrong ETag
curl -i -X PUT http://127.0.0.1:8000/codes/412/document -H 'If-Match: "wrong"' -H "Content-Type: application/json" -d '{}'
```

### Validation — 400 vs 422

```bash
# 400: malformed JSON
curl -i -X POST http://127.0.0.1:8000/codes/400 -H "Content-Type: application/json" -d 'not-json'

# 422: valid JSON, invalid business rules
curl -i -X POST http://127.0.0.1:8000/codes/422 -H "Content-Type: application/json" \
  -d '{"email":"a@b.com","start_date":"2026-06-01","end_date":"2026-01-01"}'
```

### Rate limit — 429

```bash
for i in $(seq 1 8); do curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/codes/429; done
```

### Redirects — 301–308

```bash
curl -i http://127.0.0.1:8000/codes/301
curl -i -X POST http://127.0.0.1:8000/codes/303
curl -i -X PUT http://127.0.0.1:8000/codes/307
```

### Maintenance — 503

```bash
curl -X POST "http://127.0.0.1:8000/admin/maintenance?enabled=true"
curl -i http://127.0.0.1:8000/codes/503
curl -X POST "http://127.0.0.1:8000/admin/maintenance?enabled=false"
```

### Created — 201

```bash
curl -i -X POST http://127.0.0.1:8000/codes/201 -H "Content-Type: application/json" -d '{"name":"widget"}'
```

## Project layout

```
ResponseCodeExamples/
├── main.py              # App entry + index route
├── common.py            # Shared state + CODE_REGISTRY
├── requirements.txt
├── routes/
│   ├── informational.py # 1xx
│   ├── success.py       # 2xx
│   ├── redirection.py   # 3xx
│   ├── client_errors.py # 4xx
│   └── server_errors.py # 5xx
└── README.md
```

## Notes

- **100 Continue** / **103 Early Hints**: behavior depends on client and ASGI server; use `curl -v`.
- **101 Switching Protocols**: use a WebSocket client on `/codes/101/ws`.
- **405 Method Not Allowed**: send `POST` to `GET /codes/405` — FastAPI returns `405` with `Allow`.
- **418**: joke status for learning only — not for production APIs.
