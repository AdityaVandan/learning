# REST Request Verb Examples (FastAPI)

Runnable API that demonstrates **common REST verb semantics** (safe, idempotent, partial update, discovery) with realistic endpoints.

## What to run first (quick start)

1. Start the server (see **Run** below)
2. Open the index: `GET /` (lists all verb demos + their paths)
3. Import and run the **Postman collection** in this folder

## Setup (`learningenv`)

Use the repo-root virtualenv — do **not** create a local `venv` here.

```bash
# from repository root (learning/)
source learningenv/bin/activate
pip install -r concepts/system-design/REST/RequestVerbExamples/requirements.txt
```

## Run

```bash
source learningenv/bin/activate
cd concepts/system-design/REST/RequestVerbExamples
uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

- Index of all demos: http://127.0.0.1:8001/
- Swagger UI: http://127.0.0.1:8001/docs

## Postman (recommended)

Import:

- `RequestVerbExamples.postman_collection.json`

Collection variables:

- `baseUrl` (default `http://127.0.0.1:8001`)
- `createdItemId` (set after **POST create item**)
- `createdItemEtag` (set after **GET item**)

Notes:

- Run **POST /verbs/post/items** first so the collection can store `createdItemId`.
- `PUT` demonstrates *full replacement* and is idempotent.
- `PATCH` demonstrates *partial update*; the demo uses `If-Match` to prevent lost updates.
- `DELETE` returns `204` for existing items and `404` for unknown items (some APIs choose `204` for both).

## Project layout

```
RequestVerbExamples/
├── main.py
├── common.py
├── RequestVerbExamples.postman_collection.json
├── requirements.txt
├── routes/
│   ├── get.py
│   ├── post.py
│   ├── put.py
│   ├── patch.py
│   ├── delete.py
│   ├── head_options.py
│   └── trace_connect.py
└── README.md
```

