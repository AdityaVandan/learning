# REST API Response Codes (HTTP Status Codes)

Format: **`<code> <name>`** — description (with technical details where useful).

## 1xx — Informational

- **100 Continue** — Interim response: server has received request headers and the client should continue sending the request body (often used with `Expect: 100-continue`).
- **101 Switching Protocols** — Server agrees to switch protocols as requested by the client (e.g., HTTP → WebSocket via `Upgrade`/`Connection` headers).
- **102 Processing** — Server has accepted the request but has not completed it yet (WebDAV); prevents client timeouts for long operations.
- **103 Early Hints** — Used to send preliminary headers (commonly `Link`) before the final response, enabling preload while the server prepares the final status.

## 2xx — Success

- **200 OK** — Request succeeded. Response body typically contains the requested representation or operation result.
- **201 Created** — A new resource was created. Commonly includes `Location: <new-resource-uri>` and a representation of the created resource.
- **202 Accepted** — Request accepted for processing, but not completed yet (async). Response may include a status endpoint or job id.
- **203 Non-Authoritative Information** — Response metadata/body may be modified by a transforming proxy (rare in modern APIs).
- **204 No Content** — Request succeeded but there is no response body (often used for `DELETE` or idempotent `PUT/PATCH` when returning nothing).
- **205 Reset Content** — Instructs client to reset the view/document state (rare; mostly browser-era semantics).
- **206 Partial Content** — Server is delivering only part of the resource due to a `Range` request; includes `Content-Range`.
- **207 Multi-Status** — Multiple status codes for multiple sub-operations (WebDAV; sometimes used in batch endpoints).
- **208 Already Reported** — Members already enumerated in a previous part of the response (WebDAV).
- **226 IM Used** — Delta encoding applied; response represents a transformation of a prior representation (rare).

## 3xx — Redirection

- **300 Multiple Choices** — Multiple representations are available; client should choose (rare for APIs).
- **301 Moved Permanently** — Resource has a permanent new URI; clients may cache the redirect.
- **302 Found** — Temporary redirect (historically ambiguous method handling; many clients switch to `GET`).
- **303 See Other** — Redirect to a different resource, usually retrieved with `GET` (e.g., after `POST`, redirect to a status/result URL).
- **304 Not Modified** — Cache is still valid (used with conditional requests `If-None-Match` / `If-Modified-Since`); no body.
- **307 Temporary Redirect** — Temporary redirect **without changing the HTTP method** (unlike common `302` behavior).
- **308 Permanent Redirect** — Permanent redirect **without changing the HTTP method**.

## 4xx — Client Errors

- **400 Bad Request** — Malformed request (invalid JSON, missing required fields, invalid query params). Use when the client can fix and retry.
- **401 Unauthorized** — Authentication is required or failed. Typically includes `WWW-Authenticate` for the auth scheme.
- **402 Payment Required** — Reserved; sometimes used by proprietary APIs for billing/quotas (not standardized for general use).
- **403 Forbidden** — Authenticated but not allowed (insufficient permissions, blocked by policy).
- **404 Not Found** — Resource does not exist, or the server chooses not to reveal its existence.
- **405 Method Not Allowed** — HTTP method not supported for this resource; should include `Allow: GET, POST, ...`.
- **406 Not Acceptable** — Cannot produce a representation matching the request’s `Accept` headers (content negotiation failure).
- **407 Proxy Authentication Required** — Authentication required by a proxy (rare in typical REST backends).
- **408 Request Timeout** — Server timed out waiting for the request (or an upstream did). Client may retry.
- **409 Conflict** — Request conflicts with current server state (e.g., version conflict, duplicate unique field, incompatible state transition).
- **410 Gone** — Resource permanently removed and will not be available again (useful for hard-deprecation).
- **411 Length Required** — Missing `Content-Length` where required (rare; chunked encoding usually avoids this).
- **412 Precondition Failed** — One or more preconditions in headers failed (e.g., `If-Match` with ETag did not match).
- **413 Content Too Large** — Request entity too large (formerly “Payload Too Large”). Often returned by gateways as well.
- **414 URI Too Long** — URI exceeds server limits (very long query strings).
- **415 Unsupported Media Type** — Unsupported `Content-Type` (e.g., server expects `application/json` but got `text/plain`).
- **416 Range Not Satisfiable** — Requested `Range` cannot be fulfilled; may include `Content-Range: */<size>`.
- **417 Expectation Failed** — Server cannot meet requirements of `Expect` request header (rare).
- **418 I'm a teapot** — Non-standard / joke status; sometimes used as a placeholder (not recommended for production APIs).
- **421 Misdirected Request** — Request was directed to a server that cannot produce a response (often related to connection reuse / SNI / HTTP/2).
- **422 Unprocessable Content** — Syntactically correct but semantically invalid (validation errors; WebDAV; widely used for field-level validation).
- **423 Locked** — Resource is locked (WebDAV; sometimes used when a resource is in an exclusive operation state).
- **424 Failed Dependency** — Request failed due to failure of a previous request (WebDAV; batch-like workflows).
- **425 Too Early** — Server is unwilling to risk processing a request that might be replayed (early data / anti-replay scenarios).
- **426 Upgrade Required** — Client must switch to a different protocol (e.g., require TLS or a newer HTTP version).
- **428 Precondition Required** — Server requires preconditions (commonly to enforce concurrency control using `If-Match` / ETags).
- **429 Too Many Requests** — Rate limit exceeded. Often includes `Retry-After` and/or rate limit headers.
- **431 Request Header Fields Too Large** — Headers too large (e.g., oversized cookies / auth headers).
- **451 Unavailable For Legal Reasons** — Access denied due to legal demand (takedown, geofencing by law).

## 5xx — Server Errors

- **500 Internal Server Error** — Generic server-side failure; use when no more specific 5xx applies.
- **501 Not Implemented** — Server does not support the requested functionality/method (capability not implemented).
- **502 Bad Gateway** — Gateway/proxy received an invalid response from an upstream server.
- **503 Service Unavailable** — Service temporarily unavailable (maintenance, overload). Often includes `Retry-After`.
- **504 Gateway Timeout** — Gateway/proxy timed out waiting for an upstream response.
- **505 HTTP Version Not Supported** — Server does not support the HTTP version used in the request.
- **506 Variant Also Negotiates** — Content negotiation misconfiguration (rare).
- **507 Insufficient Storage** — Server cannot store the representation needed to complete the request (WebDAV).
- **508 Loop Detected** — Infinite loop detected while processing request (WebDAV).
- **510 Not Extended** — Further extensions to the request are required (rare).
- **511 Network Authentication Required** — Authentication required to gain network access (often captive portals; rare for typical APIs).

## Practical Notes (REST-focused)

- **Prefer `400` vs `422`**:
  - Use **`400`** for malformed syntax/structure (invalid JSON, invalid parameter types, missing required parameters).
  - Use **`422`** for semantically invalid content (field validation failures like “email already used”, “startDate must be before endDate”).
- **Auth vs permission**:
  - **`401`**: not authenticated / invalid credentials / missing token.
  - **`403`**: authenticated but not authorized.
- **Caching & conditional requests**:
  - **`304`** is paired with ETags (`If-None-Match`) or modification dates (`If-Modified-Since`) to avoid re-downloading unchanged resources.

