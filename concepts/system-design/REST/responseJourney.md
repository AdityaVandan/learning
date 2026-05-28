# REST Response Code Journey (Decision Guides)

This doc is meant to help you pick **which HTTP status code to return** during API development.

Reference: [`ResponseCodes.md`](./ResponseCodes.md)

## Journey 1: End-to-end request decision flow (most common REST cases)

```mermaid
flowchart TD
  start[Request_received] --> authCheck[Auth_required?]
  authCheck -->|No| parseCheck[Can_parse_request?]
  authCheck -->|Yes| hasCreds[Authorization_present_and_valid?]

  hasCreds -->|No| r401["401 Unauthorized\nMissing/invalid credentials\n(WWW-Authenticate)"]
  hasCreds -->|Yes| permCheck[Has_permission?]
  permCheck -->|No| r403["403 Forbidden\nAuthenticated but not allowed"]
  permCheck -->|Yes| parseCheck

  parseCheck -->|No| r400["400 Bad Request\nMalformed JSON/invalid types/invalid syntax"]
  parseCheck -->|Yes| mediaCheck[Supported_Content-Type?]
  mediaCheck -->|No| r415["415 Unsupported Media Type\nWrong Content-Type"]
  mediaCheck -->|Yes| acceptCheck[Can_produce_Accept?]
  acceptCheck -->|No| r406["406 Not Acceptable\nCannot satisfy Accept"]
  acceptCheck -->|Yes| routeCheck[Route_exists?]

  routeCheck -->|No| r404["404 Not Found\nUnknown resource/path"]
  routeCheck -->|Yes| methodCheck[Method_allowed_on_route?]
  methodCheck -->|No| r405["405 Method Not Allowed\nAllow: ..."]
  methodCheck -->|Yes| idCheck[Resource_exists?]

  idCheck -->|No| r404b["404 Not Found\nResource id missing"]
  idCheck -->|Yes| goneCheck[Resource_permanently_removed?]
  goneCheck -->|Yes| r410["410 Gone\nDeprecated/removed permanently"]
  goneCheck -->|No| stateCheck[Request_conflicts_with_state?]

  stateCheck -->|Yes| r409["409 Conflict\nDuplicate/invalid state transition"]
  stateCheck -->|No| precondRequired[Require_preconditions_for_write?]
  precondRequired -->|Yes| ifMatchPresent[If-Match present?]

  ifMatchPresent -->|No| r428["428 Precondition Required\nIf-Match needed for concurrency control"]
  ifMatchPresent -->|Yes| etagMatch[If-Match equals current ETag?]
  etagMatch -->|No| r412["412 Precondition Failed\nETag mismatch (optimistic locking)"]
  etagMatch -->|Yes| validateBusiness[Business_rules_valid?]

  validateBusiness -->|No| r422["422 Unprocessable Content\nValid JSON but semantic validation failed"]
  validateBusiness -->|Yes| rateLimit[Rate_limit_exceeded?]
  rateLimit -->|Yes| r429["429 Too Many Requests\nRetry-After recommended"]
  rateLimit -->|No| successPath[Success_path]

  successPath --> actionType[Operation_type?]
  actionType -->|Read| r200["200 OK\nReturn representation"]
  actionType -->|Create| r201["201 Created\nLocation: /resource/{id}"]
  actionType -->|Delete_no_body| r204["204 No Content\nSuccess with empty body"]
  actionType -->|Async| r202["202 Accepted\nReturn job id/status URL"]
  actionType -->|Reset_client_state| r205["205 Reset Content\nClient should reset UI"]
```

## Journey 2: Caching / conditional GET (304 vs 200)

```mermaid
flowchart TD
  cacheStart[GET_with_cache_headers] --> hasIfNone[If-None-Match present?]
  hasIfNone -->|Yes| etagEquals[ETag matches?]
  etagEquals -->|Yes| r304["304 Not Modified\nNo body; keep cached response"]
  etagEquals -->|No| r200["200 OK\nReturn body + ETag"]
  hasIfNone -->|No| hasIfMod[If-Modified-Since present?]
  hasIfMod -->|Yes| modifiedCheck[Resource_modified_since?]
  modifiedCheck -->|No| r304b["304 Not Modified\nNo body"]
  modifiedCheck -->|Yes| r200b["200 OK\nReturn body + Last-Modified"]
  hasIfMod -->|No| r200c["200 OK\nReturn body + validators (ETag/Last-Modified)"]
```

## Journey 3: Downloads / streaming (206 vs 416 vs 200)

```mermaid
flowchart TD
  rangeStart[Download_request] --> hasRange[Range header present?]
  hasRange -->|No| r200["200 OK\nReturn full content"]
  hasRange -->|Yes| parseRange[Range valid & within bounds?]
  parseRange -->|No| r416["416 Range Not Satisfiable\nContent-Range: bytes */<size>"]
  parseRange -->|Yes| r206["206 Partial Content\nContent-Range: bytes start-end/size"]
```

## Journey 4: Server-side / gateway failures (5xx selection)

```mermaid
flowchart TD
  serverStart[Server_processing] --> upstreamCall[Calling_upstream_service?]
  upstreamCall -->|Yes| upstreamOk[Upstream_response_valid?]
  upstreamOk -->|No| r502["502 Bad Gateway\nUpstream returned invalid response"]
  upstreamOk -->|Yes| upstreamTimedOut[Upstream_timed_out?]
  upstreamTimedOut -->|Yes| r504["504 Gateway Timeout\nUpstream exceeded gateway timeout"]
  upstreamTimedOut -->|No| proceed[Proceed]

  upstreamCall -->|No| proceed
  proceed --> maintenance[Service_in_maintenance_or_overloaded?]
  maintenance -->|Yes| r503["503 Service Unavailable\nRetry-After recommended"]
  maintenance -->|No| bug[Unexpected_unhandled_error?]
  bug -->|Yes| r500["500 Internal Server Error\nUnexpected server failure"]
  bug -->|No| done[Return appropriate 2xx/4xx]
```

## Journey 5: Redirect choice (301/302/303/307/308)

```mermaid
flowchart TD
  redirects[Redirect_decision] --> permanent[Permanent_move?]
  permanent -->|Yes| preserveMethodP[Need_method_preserved?]
  preserveMethodP -->|Yes| r308["308 Permanent Redirect\nMethod preserved"]
  preserveMethodP -->|No| r301["301 Moved Permanently\nCommon for GET resources"]

  permanent -->|No| preserveMethodT[Need_method_preserved?]
  preserveMethodT -->|Yes| r307["307 Temporary Redirect\nMethod preserved"]
  preserveMethodT -->|No| postToGet[After_POST_redirect_to_GET_result?]
  postToGet -->|Yes| r303["303 See Other\nPOST -> GET result URL"]
  postToGet -->|No| r302["302 Found\nTemporary; clients may switch to GET"]
```

