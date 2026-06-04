# Access Tokens and Refresh Tokens: A Production Engineer's Guide

## 1. Introduction

HTTP is stateless. Every request arrives at the server with no inherent memory of the requests that came before it. This is fine for serving static pages, but it breaks the moment a user logs in and expects the application to remember them on the next click, the next minute, the next day.

Authentication answers a single question. Who is making this request? Authorization is the follow-up. Is this person allowed to do what they're asking to do? These are distinct concerns. A correctly authenticated user can still be forbidden from performing an action. An unauthenticated request usually cannot get far enough to even ask.

The session continuity problem is what we're really solving. A user types their password once. Then for the next several hours or days, every API request they make has to carry some proof that they already proved who they were. The history of web authentication is the history of figuring out what that proof should look like, where it should live, and how long it should last.

The two dominant approaches are sessions and tokens. Sessions store identity on the server and hand the client a pointer. Tokens carry identity inside the credential itself. Modern systems usually pick tokens, often a pair of them: a short-lived access token for actual API calls, and a long-lived refresh token used only to mint new access tokens. This article walks through both, end to end, with the implementation details that matter in production.

## 2. Evolution of Session Management

### Cookie-based sessions

The classic web pattern stores session state on the server. When a user logs in, the server creates a session record, gives it a random opaque ID, and sends that ID back as a cookie. Every subsequent request includes the cookie, and the server looks up the record to figure out who the user is.

```text
Browser              Server
+--------+        +-----------+        +----------------+
|        |  POST  |           |        |                |
| Login  |------->|  /login   |------->| Session Store  |
|        |        |           | write  |  sid=abc123    |
|        |        |           |        |  user_id=42    |
|        |<-------|           |        |                |
|        | Set-Cookie: sid=abc123      +----------------+
+--------+        +-----------+
```

This approach has clean revocation semantics. Logging a user out is just deleting their session row. Forcing logout everywhere is a single SQL DELETE. There's no cryptographic puzzle to solve.

The trouble starts when one server becomes many. If a load balancer routes requests across three application servers, an in-memory session map on server A is invisible to servers B and C. The standard fixes are sticky sessions, which tie a user to a specific server (and lose load balancing benefits and resilience), or a shared session store such as Redis, which every server hits on every authenticated request.

```text
                  +----+
            +---->| A  |---+
            |     +----+   |
+--------+  |     +----+   |    +-------+
| LoadBal|--+---->| B  |---+--->| Redis |
+--------+  |     +----+   |    +-------+
            |     +----+   |
            +---->| C  |---+
```

Redis works. Hundreds of millions of users have authenticated through that exact topology. But it adds a hot dependency on every request, and Redis becomes a single point of failure that needs its own replication, failover, and capacity planning. Token-based authentication emerged partly to avoid this lookup on the hot path.

## 3. Token-Based Authentication

A token is a credential the client holds and presents on every request. The server validates the token and, if valid, treats the request as authenticated. The shape of the token determines how validation works.

Opaque tokens are random strings with no internal structure. They carry no information; the server must look them up in a database to know what they mean. Functionally they behave like session IDs with a different name.

Self-contained tokens carry their own claims inside the credential. The server validates them by checking a cryptographic signature rather than by hitting a database. JSON Web Tokens are the dominant format. They make stateless validation possible, which is the property that lets you scale authentication horizontally without a session store.

A typical OAuth 2.0 / OpenID Connect deployment issues three kinds of tokens. Access tokens authorize API calls. Refresh tokens are used only to obtain new access tokens. ID tokens carry information about who the user is, intended for the client application itself rather than for an API.

## 4. Access Tokens

An access token is the credential a client sends with every API request to prove it's allowed to make that call. It's the workhorse of the system. If you're calling a protected endpoint, you're sending an access token.

The defining property of an access token is that it should be short-lived. Typical lifetimes range from five minutes to one hour, with fifteen minutes being a common default. There is no rule here, only tradeoffs. The shorter the lifetime, the smaller the window an attacker has if they steal one, and the faster permission changes propagate. The longer the lifetime, the less load on the auth service from constant refreshes.

The reason access tokens are usually JWTs (and not opaque) is throughput. A microservices fleet might process tens of thousands of authenticated requests per second. Doing a database lookup on every one of them to validate a token is expensive. A JWT can be validated using only a public key and a few microseconds of CPU. That tradeoff (cheap validation in exchange for harder revocation) is the central design decision in modern auth.

## 5. JWT Deep Dive

A JWT is three base64url-encoded segments joined by dots:

```text
eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMjMifQ.MEUCIQDx...
\_______header_____/ \_____payload____/ \_signature_/
```

### Header

The header identifies the signing algorithm and token type. It's the smallest part of the token but it matters: an attacker who can manipulate the header can sometimes attack the signature scheme itself.

```json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "2024-01-key"
}
```

The `kid` (key ID) claim is what makes key rotation work. The auth service can sign with one key while still publishing the previous key for validation, and consumers know which key to use based on the `kid` in the header.

### Payload (Claims)

The payload is a JSON object of claims. The IETF reserves a small set of standardized claim names; everything else is application-specific.

```json
{
  "iss": "https://auth.example.com",
  "sub": "user_8f3e2a91",
  "aud": "https://api.example.com",
  "iat": 1717180800,
  "nbf": 1717180800,
  "exp": 1717181700,
  "jti": "a7c4e2d1-9b8f-4e3a-b1c5-7f2e9d8a6b4c",
  "scope": "read:profile write:posts",
  "roles": ["editor"]
}
```

The standardized claims serve specific functions. `iss` identifies the issuer, the auth service that minted the token. `sub` is the subject, almost always the user ID. `aud` declares the intended audience, the service or services that should accept this token. `iat` is when the token was issued. `nbf` (not before) is the earliest time the token is valid, useful for tokens that should be activated in the future. `exp` is the expiration timestamp. `jti` is a unique token identifier, useful for deduplication and for revocation lists.

The payload is not encrypted. Anyone who has the token can decode and read every claim. This is a frequent source of bugs: developers put information in a JWT that they thought was secret, then someone with the token reads it. If a claim needs to be private, the token needs to be encrypted (JWE), or the data should never be in the token at all.

### Signature

The signature is computed over the header and payload using the algorithm declared in the header. The choice of algorithm splits into two families.

Symmetric algorithms (HS256, HS384, HS512) use the same secret to sign and verify. They're fast but require every service that validates tokens to have access to the secret. If one service is compromised, the secret leaks and an attacker can forge tokens.

Asymmetric algorithms (RS256, RS384, ES256) use a private key to sign and a public key to verify. The auth service holds the private key; every other service only needs the public key. This is the standard choice for distributed systems because the blast radius of a compromised microservice doesn't include the ability to forge tokens.

ES256 (ECDSA with P-256 and SHA-256) is increasingly preferred over RS256. Signatures are dramatically smaller (about 64 bytes versus 256 bytes for RSA-2048), keys are smaller, and operations are faster. RS256 remains common because of broader historical support.

## 6. JWT Validation Flow

The client sends the access token in the Authorization header:

```http
GET /api/orders/42 HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiI4ZjNlMmE5MSJ9.MEUCIQ...
```

Validation has a fixed checklist. Skipping any step is a security bug.

First, parse the token structurally. Reject anything that isn't three base64url segments separated by dots.

Second, verify the signature using the public key corresponding to the `kid` in the header. If the algorithm in the header isn't one your service has explicitly allowlisted, reject the token. This guards against algorithm confusion attacks where an attacker forges a token claiming `alg: none` or swaps RS256 for HS256.

Third, verify temporal claims. The current time must be greater than or equal to `nbf` (if present) and strictly less than `exp`. Apply a small clock skew tolerance (30 to 60 seconds is typical) to accommodate drift between servers.

Fourth, verify `iss` matches the expected issuer. A token from a different auth system, even if cryptographically valid against a different key, should be rejected.

Fifth, verify `aud` contains your service's identifier. Audience validation is the claim most often skipped, and it's the most dangerous one to skip in a multi-service environment. If service B accepts tokens minted for service A, then a compromised service A can pivot into service B.

Only after all five checks pass should the service treat the request as authenticated and proceed to authorization.

## 7. Why Access Tokens Expire

If access tokens never expired, the security model would collapse the first time one leaked. And tokens do leak. They leak through proxy logs, browser extensions, error reporting tools, cached request inspection panels, accidentally committed code, and exfiltration via XSS.

Short expiration limits the blast radius. A token stolen at 10:00 AM with a 15-minute lifetime stops working at 10:15. The attacker either has to pivot quickly or find a way to steal the refresh token too, which is harder because the refresh token is sent over the wire much less often.

There's a second, less obvious reason. Authorization state changes. A user gets demoted, a role gets revoked, a contractor's account gets disabled. Because JWTs are usually validated without a database lookup, the server has no way to know the user's permissions changed until the token expires and the next access token reflects the new state. The shorter the access token lifetime, the faster permission changes propagate. A 15-minute access token means at most 15 minutes of authorization staleness, which is acceptable for most applications. A 24-hour access token means a fired employee can keep using their access for a day.

This is the principle of least privilege applied across time. Don't grant more access than necessary, and don't grant it for longer than necessary.

## 8. Refresh Tokens

A refresh token is a credential whose only purpose is to obtain new access tokens. It's the second half of the token pair.

The defining characteristics of a refresh token are inverted from those of an access token. It's long-lived, often 30 to 90 days, sometimes longer for "remember me" scenarios. It's never sent to API services; it goes only to a single endpoint on the auth service. It's typically stored more carefully than an access token, because compromising it gives an attacker a renewable source of access tokens.

The asymmetry is the whole point. Access tokens are widely exposed (every API call sends them) but only briefly valid. Refresh tokens are narrowly exposed (only refresh requests carry them) but valid for a long time. Together they cover both axes of the threat model.

## 9. Why Refresh Tokens Exist

The naive question is: why not just use long-lived access tokens? The answer becomes clear when you think through what each request actually does.

Every access token leaves traces in many places. CDN logs, application server logs, request tracing systems, browser network panels, error reporting payloads, mobile crash reports. A token that travels everywhere is a token that ends up in places it shouldn't be. Making it short-lived means those traces stop being useful to an attacker within minutes.

But short-lived access tokens alone produce a terrible user experience. If users had to log in every 15 minutes, applications would be unusable. Refresh tokens solve the UX problem without compromising the security model. The refresh token sits in protected storage and only emerges to mint a new access token, then goes back into hiding.

You can think of the pair as a hot wallet and a cold wallet. The access token is hot: spent constantly, replaced when stolen. The refresh token is cold: only touched occasionally, kept in a safer place, and worth the trouble of locking down because losing it means losing the whole session.

## 10. Authentication Lifecycle

### Login

The user authenticates once, usually with a password plus a second factor. The auth service verifies credentials and issues two tokens.

```http
POST /auth/login
Content-Type: application/json

{ "email": "u@example.com", "password": "...", "totp": "294817" }

HTTP/1.1 200 OK
Content-Type: application/json

{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_token": "rt_8f3e2a91b4c7d6e5...",
  "scope": "openid profile email"
}
```

The access token expires in 900 seconds (15 minutes). The refresh token has its own expiration tracked server-side.

### API requests

The client sends the access token with every API call. The refresh token never leaves storage during normal API use.

```http
GET /api/me HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJ...
```

The API service validates the JWT locally and proceeds. No round trip to the auth service. This is the property that makes the architecture scalable.

### Refresh

When the access token expires (or is about to), the client sends the refresh token to the auth service's refresh endpoint.

```http
POST /auth/refresh
Content-Type: application/json

{ "refresh_token": "rt_8f3e2a91b4c7d6e5..." }

HTTP/1.1 200 OK
Content-Type: application/json

{
  "access_token": "eyJ...",
  "expires_in": 900,
  "refresh_token": "rt_9c8d7e6f5a4b3c2d..."
}
```

In a rotation scheme (covered below), the response contains both a new access token and a new refresh token. The old refresh token is invalidated.

### Logout

Logout deletes the refresh token from server-side storage. The access token typically isn't revoked; it just expires naturally within minutes.

```http
POST /auth/logout
Authorization: Bearer eyJ...
Content-Type: application/json

{ "refresh_token": "rt_..." }

HTTP/1.1 204 No Content
```

This is one of the cleaner asymmetries of the design. You don't need a revocation list for access tokens because they have a short fuse. You only need to make sure no new access tokens get issued, which means killing the refresh token.

## 11. Refresh Token Storage

Where the refresh token lives on the client is one of the highest-stakes decisions in the system.

### Browser storage options

Browsers offer three locations, each with distinct security properties.

`localStorage` is accessible to any JavaScript running on the page. This means any successful XSS attack reads the refresh token and exfiltrates it. The convenience of `localStorage` (any code can read it) is exactly the property that makes it dangerous.

`sessionStorage` has the same vulnerability profile as `localStorage`, with the additional downside that the token is lost on tab close. This makes it useful only for very short-lived sessions.

HttpOnly cookies are not accessible to JavaScript. An XSS attack cannot read the cookie value. The cookie is automatically sent on every request to the matching domain, which is convenient but also creates CSRF exposure. The standard mitigation is to combine the HttpOnly flag with the SameSite attribute (`SameSite=Strict` or `SameSite=Lax`) and the Secure flag (cookie only sent over HTTPS).

The practical recommendation for most web applications is HttpOnly + SameSite + Secure cookies for refresh tokens, with the refresh endpoint scoped to a path that no other request touches. This minimizes both XSS exposure (cookie is invisible to JS) and CSRF exposure (SameSite limits cross-origin sends).

### Mobile storage options

Mobile platforms provide hardware-backed secure storage that's substantially more secure than anything available in browsers.

On iOS, the Keychain stores credentials behind the device's secure enclave. Access can be gated on biometric authentication, requiring the user to authenticate before the refresh token is even readable.

On Android, the Keystore performs the same role. Modern devices back keystore-protected keys with hardware (Trusted Execution Environment or StrongBox), so even root access on the device doesn't directly expose the key material.

The mobile threat model is different from the browser one. The dominant browser threat is XSS. The dominant mobile threat is device theft. Hardware-backed storage with biometric unlock addresses both.

### Server-side storage

The server should never store refresh tokens in plaintext. They're credentials. The same reasoning that says you should hash passwords applies here: if the database leaks, the stored tokens should not be directly usable by an attacker.

A SHA-256 hash is sufficient. Refresh tokens are random high-entropy strings, so they don't need the slow, salted hashes (bcrypt, Argon2) that user passwords need to defend against brute-force attacks. The hash protects against database dumps; that's the whole job.

```python
import hashlib

def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
```

When a refresh request comes in, hash the incoming token and look up by hash. Never store the raw value.

## 12. Refresh Token Database Design

A workable schema captures who the token belongs to, what device it's on, when it was issued, when it expires, whether it's been used or revoked, and what token replaced it (for rotation tracking).

```sql
CREATE TABLE refresh_tokens (
    id              UUID PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id),
    token_hash      VARCHAR(64) NOT NULL UNIQUE,
    family_id       UUID NOT NULL,
    device_id       VARCHAR(255),
    device_name     VARCHAR(255),
    user_agent      TEXT,
    ip_address      INET,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,
    last_used_at    TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ,
    revoked_reason  VARCHAR(50),
    replaced_by     UUID REFERENCES refresh_tokens(id)
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_refresh_tokens_family ON refresh_tokens(family_id);
CREATE INDEX idx_refresh_tokens_expires ON refresh_tokens(expires_at) WHERE revoked_at IS NULL;
```

Each column has a job. `user_id` is the obvious link to the user. `token_hash` is what you look up by; the raw token is never stored. `family_id` ties together every token in a rotation chain (more on this in the next section). `device_id` and `device_name` make "log out from all devices" usable and let users see active sessions in account settings. `user_agent` and `ip_address` support audit trails and anomaly detection. `created_at` and `expires_at` track lifetime. `last_used_at` supports inactivity-based expiration. `revoked_at` and `revoked_reason` track why a token died, which matters for debugging and security investigation. `replaced_by` lets you trace a rotation chain forward.

The partial indexes are not cosmetic. A production refresh token table tends to be heavily skewed toward revoked rows over time, and indexes that include revoked rows degrade quickly. Filtering on `revoked_at IS NULL` keeps the hot path fast.

## 13. Refresh Token Rotation

Rotation is the practice of issuing a new refresh token every time an old one is used, and immediately invalidating the old one. Each refresh request both renews the access token and replaces the refresh token.

Without rotation, a refresh token works for its full lifetime. If it's stolen, the attacker has 30 to 90 days of guaranteed access until it expires naturally. With rotation, every successful refresh produces a new token; the previous one can never be used again. The window shrinks dramatically.

Conceptually, a token family is a chain: the user logs in and receives token A. They use A to refresh, getting B. They use B to refresh, getting C. Each new token's `family_id` points back to the original. If any token in the chain is used after it has been replaced, the system has evidence that something is wrong.

The implementation is straightforward. On every refresh request:

```python
def refresh(raw_token: str) -> TokenPair:
    token_hash = sha256(raw_token)
    record = db.refresh_tokens.find_by(token_hash=token_hash)

    if record is None:
        raise InvalidToken()

    if record.expires_at < now():
        raise ExpiredToken()

    if record.revoked_at is not None:
        # Reuse detected. Burn the entire family.
        db.refresh_tokens.revoke_family(record.family_id, reason="reuse_detected")
        raise SecurityViolation("Refresh token reuse detected")

    new_refresh = generate_refresh_token()
    new_access = mint_access_jwt(record.user_id)

    db.transaction:
        db.refresh_tokens.create(
            user_id=record.user_id,
            token_hash=sha256(new_refresh),
            family_id=record.family_id,
            device_id=record.device_id,
            expires_at=now() + timedelta(days=30),
        )
        db.refresh_tokens.update(record.id,
            revoked_at=now(),
            revoked_reason="rotated",
            replaced_by=new_record.id,
        )

    return TokenPair(access=new_access, refresh=new_refresh)
```

The transaction matters. The new token must be created and the old one revoked atomically, or a crash between the two steps will lock the user out (or give them two valid tokens, depending on which happens first).

## 14. Refresh Token Reuse Detection

Reuse detection is what makes rotation worth the complexity. It's how you find out a token was stolen.

The scenario: an attacker steals refresh token A from the user's device. The legitimate user, unaware of the theft, uses A first. A is rotated into B. Now both the attacker and the legitimate user have references the attacker still holds A. When the attacker tries to use A, the server sees that A has already been revoked and replaced.

This is unambiguous evidence of theft. There is no benign explanation for using a token that's already been rotated. The correct response is to revoke every token in the same family. Both the attacker and the legitimate user lose access. The legitimate user has to log in again. This is the right outcome: we don't know which party is which, and locking everyone out and forcing fresh authentication is the only safe choice.

The reverse scenario also gets caught. The attacker uses A first and rotates it into B. The legitimate user later tries A. Same detection, same response.

There is one annoying false positive. Network failures can leave a client uncertain whether a refresh succeeded. The client retries with the old token. The server sees an old, revoked token and triggers reuse detection. To avoid this, clients should treat refresh as carefully as a financial transaction: serialize concurrent refreshes, persist the new token before discarding the old, and only retry after explicit confirmation of failure. Some implementations also grant a brief grace period where the immediately-previous token is treated as if it were the current one, which trades a small security window for fewer false positives.

## 15. Access Token Revocation Problem

JWTs are stateless by design. The server validates them without consulting any database. This is what makes them fast and scalable. It's also what makes them hard to revoke.

If a user is fired, their permissions change, or their account is compromised, you'd like to invalidate their current access token immediately. But the API services validating those tokens have no idea anything has changed. They check the signature, check the expiration, check the audience, and let the request through. Until the access token expires naturally, the user keeps having access.

This is the fundamental tradeoff. Stateless validation gives you O(1) verification with no database hops. The cost is that you can't yank a valid token mid-flight. Most production systems accept this tradeoff and compensate by keeping access tokens short.

## 16. JWT Blacklists / Denylists

The naive solution is to keep a list of revoked token IDs and check the list on every request. The list is keyed by `jti` (the unique token ID claim in the JWT) and lives in a fast store like Redis.

```python
def validate_access_token(jwt: str) -> Claims:
    claims = verify_signature_and_claims(jwt)

    if redis.exists(f"jwt_revoked:{claims['jti']}"):
        raise RevokedToken()

    return claims
```

When you need to revoke, you write the `jti` into Redis with an expiration equal to the token's remaining lifetime:

```python
def revoke_token(jti: str, exp: int) -> None:
    ttl = exp - int(time.time())
    if ttl > 0:
        redis.setex(f"jwt_revoked:{jti}", ttl, "1")
```

This works. Revocation becomes immediate. But you've reintroduced the very thing JWTs were supposed to eliminate: a database lookup on every authenticated request. At scale, this is a significant cost. You're now back to the same operational profile as opaque tokens (Redis on the hot path), with the additional complexity of JWT signing and validation on top.

## 17. Why Most Systems Avoid JWT Blacklists

The dominant production pattern is to skip blacklists entirely and keep access tokens short. A 15-minute access token bounds the worst-case window of unauthorized access at 15 minutes. For most use cases, that's acceptable.

The alternative is to use blacklists only for sensitive scenarios: password changes, explicit "log out everywhere", suspected account compromise. The blacklist exists but it's small and rarely consulted. Most requests still validate purely against the signature.

Some systems split the difference: validate the signature on every request (cheap) and check a small bloom filter or local cache of recently revoked tokens (also cheap). The cache is kept in sync via pub/sub from the auth service. Falses positives in the bloom filter trigger a Redis check; false positives are rare, so the hot path stays fast.

The right answer depends on the application. Banking and healthcare often justify the blacklist cost. Most consumer applications don't. The interview-style answer is: short access tokens are usually sufficient, and revocation goes through the refresh token, not the access token.

## 18. OAuth 2.0 Context

OAuth 2.0 is the framework that gave us the modern access/refresh token vocabulary. It's worth knowing the roles even if you never implement an OAuth server yourself.

The Resource Owner is the human user. The Client is the application requesting access on their behalf (a mobile app, a web app, a third-party service). The Authorization Server issues tokens. The Resource Server hosts the protected APIs and validates the tokens.

In a simple deployment all three server roles can be a single service. In larger systems they're separate. The OAuth specification was designed for the third-party delegation case (when you sign into a site using your Google account), but the same patterns apply equally well to first-party authentication (when an application authenticates its own users).

### Authorization Code Flow

The Authorization Code flow is the standard pattern for browser-based and mobile clients. The high-level sequence:

The user clicks "sign in". The application redirects them to the authorization server with the application's client ID and a redirect URI. The user authenticates at the authorization server. The authorization server redirects the user back to the application's redirect URI, carrying a short-lived authorization code in the URL. The application sends the authorization code to the authorization server from its backend, along with its client secret. The authorization server returns access and refresh tokens.

The reason for the indirection (code first, then exchange) is that the redirect URL passes through the user's browser, where it's exposed in browser history, referrer headers, and so on. The authorization code is single-use and short-lived (typically 60 seconds), so its exposure isn't damaging. The actual tokens are exchanged server-to-server, never touching the browser.

### PKCE

PKCE (Proof Key for Code Exchange) is what makes the Authorization Code flow safe for clients that can't keep a client secret, primarily mobile and single-page applications.

The client generates a random secret called the `code_verifier` and a derived `code_challenge`:

```python
code_verifier = secrets.token_urlsafe(64)
code_challenge = base64url(sha256(code_verifier.encode("ascii"))).rstrip("=")
```

The client sends the `code_challenge` (not the verifier) in the initial authorization request. When it later exchanges the authorization code for tokens, it sends the `code_verifier`. The authorization server hashes the verifier and checks that it matches the original challenge. An attacker who intercepts the authorization code can't redeem it without the verifier, which never crossed the network in plaintext.

PKCE is now required for all OAuth 2.0 public clients per the latest IETF guidance (OAuth 2.0 Security Best Current Practice). It's no longer optional.

## 19. OpenID Connect

OAuth 2.0 is fundamentally an authorization framework. It tells you what a client is allowed to do; it doesn't tell you who the user is. People used OAuth for authentication anyway by abusing the access token, treating successful API calls as proof of identity, which is a famously bad idea.

OpenID Connect is a thin layer on top of OAuth 2.0 that adds proper authentication. It introduces a third token type: the ID Token.

An ID Token is a JWT that contains user identity information. Unlike access tokens, ID tokens are intended for the client application, not for an API. The application reads the ID token to find out who just logged in.

```json
{
  "iss": "https://auth.example.com",
  "sub": "user_8f3e2a91",
  "aud": "client_application_id",
  "exp": 1717181700,
  "iat": 1717180800,
  "nonce": "n-0S6_WzA2Mj",
  "auth_time": 1717180800,
  "name": "Jane Doe",
  "email": "jane@example.com",
  "email_verified": true,
  "picture": "https://cdn.example.com/u/jane.jpg"
}
```

The `aud` claim points to the client application, not to an API. The `nonce` claim binds the ID token to the original authorization request, preventing token replay. The `auth_time` claim records when the user actually authenticated (useful for forcing re-auth after a period of inactivity).

The mental model: the access token is for talking to APIs, the ID token is for the application to learn who the user is, the refresh token is for getting new access tokens. Three tokens, three jobs.

## 20. Access Token vs Refresh Token vs ID Token

| Property | Access Token | Refresh Token | ID Token |
|---|---|---|---|
| Purpose | Authorize API calls | Obtain new access tokens | Identify the authenticated user |
| Audience | Resource Server (APIs) | Authorization Server | Client Application |
| Typical lifetime | 5 to 60 minutes | 30 to 90 days | Same as access token, often unused after login |
| Format | Usually JWT (sometimes opaque) | Usually opaque random string | Always JWT |
| Carries user identity | Sometimes (subset of claims) | No | Yes (full profile claims) |
| Sent on every API request | Yes | No | No |
| Server-side storage | Usually none | Hashed in database | Usually none |
| Revocable | Indirectly (via short lifetime or denylist) | Directly (delete server record) | Not typically revoked |
| Used for authorization decisions | Yes | No | No |
| Used for authentication assertion | No | No | Yes |

The most common confusion is between access tokens and ID tokens. They look identical on the wire (both are JWTs). The difference is intent. An access token says "the bearer of this token is allowed to call API X". An ID token says "the user named in this token authenticated at time Y". The `aud` claim disambiguates them. APIs should accept tokens with an `aud` matching the API; client applications should accept ID tokens with an `aud` matching the client.

## 21. Microservices Architecture

In a microservices environment, the question becomes: where does token validation happen?

The three common patterns:

The API Gateway pattern centralizes validation at the edge. The gateway validates the JWT once and forwards a stripped-down representation of the user (often just a header like `X-User-Id`) to downstream services. Services trust the gateway and don't re-validate. This is the simplest pattern and reduces validation overhead, but it depends on network isolation between the gateway and the services. Anyone who can talk to a service directly, bypassing the gateway, can impersonate any user.

The Service Mesh pattern delegates validation to a sidecar proxy (Envoy with the JWT filter, Istio, Linkerd). Every service in the mesh has a sidecar that validates incoming requests before they reach the application code. The application code is freed from validation duties. This pattern works well for large fleets and provides defense in depth: even if a service is reached directly, the sidecar still enforces validation.

The Per-Service Validation pattern has each service validate tokens independently using a shared library. This is more code duplication but eliminates trust assumptions about the network. It's the right choice when you can't guarantee that services are unreachable except through the gateway.

The decision is usually driven by infrastructure maturity. Greenfield projects with a service mesh tend toward sidecar validation. Older systems with established gateways tend toward gateway validation. The least-good answer is "the gateway validates and we don't bother in services", combined with a flat network that lets anything talk to anything.

## 22. Public Key Infrastructure

For asymmetric JWT signing to work at scale, services need a reliable way to discover the public keys they should trust.

The standard mechanism is JWKS (JSON Web Key Set). The auth service exposes a well-known endpoint that publishes its current public keys:

```http
GET /.well-known/jwks.json HTTP/1.1
Host: auth.example.com

HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: max-age=3600

{
  "keys": [
    {
      "kty": "RSA",
      "kid": "2024-q2",
      "use": "sig",
      "alg": "RS256",
      "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4...",
      "e": "AQAB"
    },
    {
      "kty": "RSA",
      "kid": "2024-q1",
      "use": "sig",
      "alg": "RS256",
      "n": "...",
      "e": "AQAB"
    }
  ]
}
```

Services fetch the JWKS at startup, cache it, and refresh periodically. When validating a token, they look at the `kid` in the JWT header and pick the matching key from the cache. If the `kid` isn't in the cache, they refresh the JWKS once (in case a new key was just added) and try again before failing.

Notice that the JWKS contains multiple keys. This is critical for rotation.

## 23. Key Rotation

Signing keys should be rotated periodically. Standard cadences range from quarterly to annually, with emergency rotation procedures for suspected compromise. Rotation must happen without downtime, which means there's always a window where both the old and new keys are valid.

The procedure:

Add the new key to the JWKS while continuing to sign with the old key. Services pick up the new key on their next JWKS refresh. After enough time has passed that all services have refreshed (longer than your JWKS cache TTL plus a safety margin), switch signing to the new key. Old tokens signed with the old key are still validated against the old key, which remains in the JWKS. After enough time has passed for all old tokens to expire naturally (longer than your access token lifetime plus refresh windows), remove the old key from the JWKS.

The `kid` claim is what makes this work. Without it, services would have to try every key in the JWKS to validate each token, which is wasteful. With it, the service goes straight to the right key.

Emergency rotation skips the gradual rollout. You publish the new key, switch signing immediately, and accept that any token signed with the old key after the cutover will fail validation. Users get logged out. That's the price of suspecting key compromise.

## 24. Security Threats

Each of these is worth tracking. The pattern in each case is the same: name the threat, name the impact, name the mitigation.

**Token Theft via XSS.** Malicious JavaScript reads tokens from `localStorage` and exfiltrates them. Mitigation: store refresh tokens in HttpOnly cookies or platform-secure storage, never in `localStorage`. Use a strong Content Security Policy. Sanitize all user-rendered content.

**Token Theft via Network Interception.** Tokens transmitted over plaintext HTTP are visible to anyone on the network path. Mitigation: HTTPS everywhere, with HSTS to prevent downgrade. No exceptions for development or staging environments if production patterns are inherited.

**CSRF on Cookie-Based Tokens.** If the refresh token is in a cookie, the browser sends it automatically on cross-origin requests, allowing forged refresh attempts. Mitigation: `SameSite=Strict` or `SameSite=Lax` on the cookie. CSRF tokens for state-changing endpoints. The refresh endpoint should also require the refresh token to be sent in a way that simple `<form>` submission can't trigger.

**Replay Attacks.** An attacker captures a valid request and resends it. Mitigation: short access token lifetimes shrink the replay window. For sensitive endpoints, request-level signing or nonces add a second layer.

**Session Fixation.** An attacker provides the victim with a known session ID, then hijacks the session after the victim authenticates. Mitigation: issue new tokens after every authentication event. Never reuse pre-authentication identifiers.

**Man-in-the-Middle.** An attacker positioned between client and server reads or modifies traffic. Mitigation: TLS with strong cipher suites, certificate pinning on mobile clients, certificate transparency monitoring.

**Refresh Token Leakage.** Refresh tokens leak through logs, error reports, or insecure storage. Mitigation: never log refresh tokens (treat them like passwords). Store hashed server-side. Use platform-secure storage on the client.

**JWT Algorithm Confusion.** Attackers send a token with `alg: none` (asserting no signature) or swap an asymmetric algorithm for a symmetric one (using the public key as the HMAC secret). Mitigation: allowlist accepted algorithms explicitly in validation code. Never trust the `alg` field to determine validation strategy.

**Weak Signing Keys.** A short or low-entropy HMAC secret can be brute-forced offline once an attacker has any valid JWT. Mitigation: 256 bits or more of cryptographic randomness for HMAC keys. Or skip HMAC entirely and use asymmetric algorithms (RS256, ES256) where this attack doesn't apply.

**The "none" Algorithm.** Some old JWT libraries accept tokens with `alg: none` (no signature) as valid. Mitigation: see above; allowlist algorithms. Use modern, maintained libraries.

**Insufficient Audience Validation.** A token minted for service A is accepted by service B because B doesn't check the `aud` claim. Mitigation: validate `aud` on every request, in every service.

## 25. Browser Security Considerations

The browser threat model is dominated by XSS. Any JavaScript-readable storage is compromised by a successful XSS attack. This single fact reshapes how you think about token storage.

`localStorage` is JavaScript-readable. Anything stored there is XSS-exposed.

`sessionStorage` is JavaScript-readable. Same exposure.

In-memory variables (a JavaScript variable holding the token) are JavaScript-readable. Same exposure. However, they're cleared on page reload, which limits persistence. The pattern of keeping the access token only in memory and the refresh token in an HttpOnly cookie is reasonable for SPAs: an XSS attack can grab the current access token but not mint new ones once it expires, because the refresh token is unreachable.

HttpOnly cookies are not JavaScript-readable. They survive XSS. They are, however, automatically attached to requests, which is the CSRF problem.

CSRF mitigation has three layers. `SameSite=Strict` cookies are not sent on any cross-site request, including top-level navigation. This is the strongest setting but breaks some legitimate flows (links from external sites that should land authenticated). `SameSite=Lax` is sent on top-level GET navigation but not on cross-site POSTs, which is the right balance for most applications. Combined with a state-changing endpoint requiring an additional CSRF token or a custom header that can only be set from JavaScript (and thus only by the legitimate origin), the CSRF surface is largely closed.

The practical pattern for SPAs: refresh token in HttpOnly + Secure + SameSite=Strict cookie, scoped to the refresh endpoint's path. Access token held only in memory in JavaScript. On page reload, the SPA hits the refresh endpoint, the cookie is sent automatically, and a new access token comes back. The refresh token never touches JavaScript.

## 26. Mobile Security Considerations

Mobile threat models differ from browser threat models in important ways.

There's no XSS equivalent on native apps. The code running in the app is your code, signed with your certificate. The XSS angle is replaced by other angles: a rooted or jailbroken device, a malicious app on the same device (less of an issue with platform sandboxing), backup extraction, and device theft.

iOS Keychain is the standard storage location. Items can be configured with access control attributes that restrict when they're readable: `kSecAttrAccessibleWhenUnlocked` (only while the device is unlocked), `kSecAttrAccessibleAfterFirstUnlock` (after the first unlock following a boot, useful for background work), and `kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly` (requires a passcode and doesn't sync via iCloud).

Android Keystore plays the equivalent role. Keys can be marked as hardware-backed and require user authentication (biometric or PIN) before use. The actual key material never leaves the hardware on modern devices with Trusted Execution Environment or StrongBox.

Biometric gating is the headline feature. You can require Face ID or Touch ID (or fingerprint on Android) before a refresh token is even readable. A thief who steals an unlocked phone can use the app while it's open, but once it backgrounds and the session needs refresh, the device's biometric requirement kicks in.

Certificate pinning is a mobile-specific protection. Apps pin the expected server certificate (or its issuer chain) and reject TLS connections to anything else. This defends against compromised root certificates and corporate proxies that some attackers can exploit on managed devices. The tradeoff is operational complexity: when your certificate rotates, apps with stale pins break. Modern approaches use pin sets with multiple acceptable certificates and shorter rotation windows.

Device compromise (root or jailbreak) effectively defeats most local protections. Detection is possible but not perfect; determined attackers can bypass detection. The realistic stance is to make rooted devices harder for attackers without pretending you can fully prevent the attack.

## 27. Scaling Authentication Systems

The architectural reason to use JWTs is throughput. Let's look at why.

A modest service handling 50,000 requests per second performs 50,000 token validations per second. If each validation is a Redis round trip (1 millisecond best case), you're saturating Redis with 50,000 ops per second per service. Multiply by the number of services in a typical microservices fleet and the auth path becomes a major piece of infrastructure cost.

JWT validation is CPU-bound, not I/O-bound. A single core can validate tens of thousands of RS256 signatures per second; ES256 is faster still. The validation happens locally with no network hops. The throughput ceiling becomes the application's general request capacity, not auth specifically.

The refresh endpoint, in contrast, does need a database. Every refresh writes (rotation) and reads (validation). But refresh happens infrequently: once every 10 to 15 minutes per active session, not once per request. A user generating 100 API requests per minute generates roughly 0.07 refresh requests per minute, a 1500x reduction in load on the stateful component.

For very large deployments, the refresh token store can be partitioned by user ID. Most refresh requests are reads followed by writes scoped to a single user, which makes user-based sharding straightforward. PostgreSQL handles tens of thousands of refresh operations per second on a single primary with reasonable hardware; partitioning extends this further.

Some systems push refresh token state into Redis (with PostgreSQL as a durable backup) because Redis handles the read/write workload more elastically. The tradeoff is durability: if Redis loses data, users get logged out. For most applications, "users get logged out on a major incident" is acceptable; for banking and similar, the durable store is the source of truth and Redis is just a cache.

## 28. Session Management

Tokens are the plumbing; sessions are what users see. The user-facing surface of session management depends on the token model but isn't identical to it.

**Single device logout.** Delete the refresh token associated with the device. The access token expires naturally within minutes. The user is logged out of that device only.

**Log out everywhere.** Delete all refresh tokens for the user. Wait for access tokens to expire (or, if you can't tolerate the delay, add the relevant `jti`s to a short-lived denylist). The user is logged out of every device.

**Active session listing.** Surface the device, browser, IP address, and last-used time for each refresh token associated with the user. Users can see "Chrome on MacBook, last used 5 minutes ago" and revoke individual sessions. This requires capturing device metadata at refresh-token issuance and keeping `last_used_at` current.

**Inactivity timeout.** Revoke refresh tokens that haven't been used in some window (commonly 30 days for consumer apps, much shorter for sensitive systems). Implement as a background job that checks `last_used_at` against a threshold.

**Concurrent session limits.** Some applications cap how many active sessions a user can have. Implement by counting non-revoked refresh tokens per user on login and revoking the oldest when the limit is exceeded. Be aware that "session" in this context is per-refresh-token, which corresponds to a device or a logical session.

**Step-up authentication.** Some actions (payment, password change) should require recent authentication regardless of session validity. Track `auth_time` in the access token; if the action requires authentication within the last 5 minutes and `auth_time` is older, force re-authentication.

## 29. Production Architectures

Real systems combine these patterns in characteristic ways depending on the use case.

**Typical SaaS application.** Access tokens of 15 to 60 minutes. Refresh tokens of 14 to 30 days with rotation enabled. Refresh tokens stored in HttpOnly cookies for web, in OS-secure storage for mobile and desktop apps. JWT signed with RS256 or ES256 and a JWKS endpoint for service discovery. Microservices validate independently via a shared library.

**Mobile-first consumer apps.** Refresh tokens lean longer (30 to 90 days) because re-authentication on mobile is a heavier user experience cost than on web. Biometric gating on the refresh token to mitigate device theft. Push-based session invalidation for high-impact events.

**Banking and high-security systems.** Access tokens of 5 minutes or less. Refresh tokens of hours, not days. Frequent step-up authentication for sensitive actions. Per-request revocation checks for some endpoints (small denylist, fast lookup). Bound tokens to client certificates or device-attested keys.

**Enterprise SSO.** SAML or OpenID Connect against a corporate identity provider. Access tokens minted by the IdP or by an internal auth service that federates to the IdP. Session lifetime controlled centrally for compliance with corporate policies.

**Consumer internet at scale.** The dominant constraint is request throughput on validation. JWT, stateless validation, no per-request database lookups. Refresh tokens stored in a partitioned PostgreSQL or comparable system. Rotation enabled. Reuse detection triggers strict session termination.

## 30. Common Mistakes

The same mistakes recur across many systems. The list, with the reasoning.

**Long-lived access tokens.** A 30-day access token undoes the entire security model. There's no point in having a refresh flow at all. Keep access tokens to minutes, not days.

**No refresh rotation.** A non-rotating refresh token works for its full lifetime if stolen. Rotation cuts this to "until the next legitimate refresh by either party". Always rotate.

**Storing raw refresh tokens.** A database leak with raw refresh tokens means every active session is compromised. Hash before storage, every time.

**Missing audience validation.** If service B accepts tokens minted for service A, a compromise of A pivots into B. Always check `aud`.

**Missing issuer validation.** Tokens from a development instance of the auth service should not be accepted in production. Check `iss`.

**Using localStorage for refresh tokens in browsers.** Any XSS reads it. HttpOnly cookie or in-memory only for access tokens.

**Trusting unsigned JWTs.** Some libraries decode JWTs without verifying signatures unless explicitly told to. Always verify. Reject `alg: none` regardless of library defaults.

**Hard-coded HMAC secrets in source code.** They leak. Use environment variables and secret management. Better, use asymmetric algorithms so there's no shared secret to leak.

**Not rotating signing keys.** A signing key that hasn't rotated in three years is at higher risk of compromise simply through time. Regular rotation makes compromise less likely and limits its blast radius when it happens.

**Ignoring clock skew.** Servers' clocks drift. A token that's "not yet valid" by 200 milliseconds will fail validation in a fleet without NTP. Add a small skew tolerance to `nbf` and `exp` checks.

**Putting sensitive data in access tokens.** Anyone with the token can read every claim. SSNs, internal user IDs that map to sensitive PII, and any other secret have no place in JWT claims.

## 31. Best Practices

The default configuration that works for most production systems:

```text
Access token lifetime:        15 minutes
Refresh token lifetime:       30 to 90 days
Refresh token rotation:       Enabled
Reuse detection:              Enabled, triggers family revocation
Signing algorithm:            RS256 or ES256 (ES256 preferred)
Key rotation cadence:         Quarterly, with emergency rotation procedure
Refresh token storage:        SHA-256 hashed in database
Client-side refresh storage:  HttpOnly+Secure+SameSite cookie (browser),
                              OS secure storage (mobile)
Transport:                    HTTPS only, HSTS enabled
Audience claim validation:    Always, on every service
Issuer claim validation:      Always
Clock skew tolerance:         30 to 60 seconds
JWKS endpoint cache:          1 hour with refresh on unknown kid
```

Deviate from these defaults only when a specific requirement justifies it. Shorter access token lifetimes for higher-security systems. Longer refresh tokens for low-friction consumer apps. Denylists only when the user-facing requirement for immediate revocation actually exists.

## 32. Interview and System Design Discussion

The questions that come up reliably in interviews and design reviews:

**Why JWT instead of opaque tokens?** Stateless validation. No database lookup on the request hot path. Scales horizontally without a shared session store. The tradeoff is that revocation becomes harder, which you mitigate with short lifetimes.

**Why refresh tokens at all?** Access tokens are short-lived for security. Re-authentication every 15 minutes is a terrible user experience. Refresh tokens decouple the security property (short access tokens) from the user experience property (long sessions).

**Stateless versus stateful authentication.** Stateless gives you O(1) validation with no I/O. Stateful gives you immediate revocation. The hybrid (stateless access tokens, stateful refresh tokens) gets you most of the benefits of both.

**How do you revoke a JWT?** You don't, normally. You wait for it to expire. For immediate revocation, you either use a denylist (introduces state) or invalidate the refresh token and wait for the access token to expire on its own.

**OAuth flows: which one when?** Authorization Code with PKCE for browser and mobile apps. Client Credentials for service-to-service. Device Code for input-constrained devices like TVs. Resource Owner Password Credentials is deprecated and shouldn't be used.

**How would you scale token validation to 1 million requests per second?** Don't touch a database. JWT with stateless validation lets you scale validation linearly with application servers. The refresh endpoint does need a database but sees orders of magnitude less traffic. Partition the refresh store by user ID once a single primary isn't enough.

**Designing authentication for a multi-tenant SaaS.** Token claims include tenant ID. Audience validation includes tenant scoping (or the API gateway enforces it). Cross-tenant access is impossible by construction, not by check.

**How do you handle a security incident where signing keys may be compromised?** Emergency key rotation. New `kid`, immediate switch in signing, publish both keys in JWKS for the existing token lifetime window. After existing tokens expire, remove the old key. Notify users; some platforms force re-authentication.

## 33. Conclusion

The two-token model is what most production systems converge on for good reasons. Access tokens give you cheap, stateless authorization checks that scale to whatever request volume you can throw at them. Refresh tokens give you the long sessions users expect, with proper revocation and theft detection. Together they hit the three axes that matter: security (short exposure window for the credential that travels), scalability (no database on the hot path), and user experience (no constant logins).

The decisions that actually matter are smaller than they look. Pick short access token lifetimes. Use asymmetric signing with proper key rotation. Rotate refresh tokens and detect reuse. Hash refresh tokens server-side. Validate every claim on every request. Pick storage on the client that matches the platform's threat model.

Most authentication bugs aren't subtle. They come from skipping one of the things on the list above, usually because it seemed unnecessary at the time. Build the boring version first.