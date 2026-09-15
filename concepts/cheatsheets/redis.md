# Redis Cheatsheet

Learning / interview revision guide for Redis, split into two parts:

1. **[Redis Base](#part-i--redis-base)** — core model, data types, cache/session patterns, ops
2. **[Redis Queue](#part-ii--redis-queue)** — lists, streams, pub/sub, delay/priority queues

**Related in this repo:** [caching strategies](../system-design/cachingStrategies/README.md) · [distributed dedup with Redis](../system-design/dedup/4_redis/main.go)

**Hands-on:** [Redis Sandbox](https://redis.io/try/sandbox/) · local: `docker run -p 6379:6379 redis:alpine` · CLI: `redis-cli`

Python examples use **[redis-py](https://redis.readthedocs.io/)**:

```python
import redis
r = redis.Redis(host="localhost", port=6379, decode_responses=True)
```

---

# Part I — Redis Base

Core Redis: keys, types, TTL, atomic patterns (cache / locks / rate limits), batching, durability, scaling, and ops.

---

## B1. What Redis Is

| Concept | Detail |
|--------|--------|
| **Definition** | In-memory data structure store used as cache, session store, broker, rate limiter, lock service, and lightweight DB |
| **Model** | Single-threaded command execution (per shard) → commands are atomic; concurrency is about *clients*, not Redis threads |
| **Access** | Key → value; values are typed (string, hash, list, set, zset, stream, …) |
| **Speed** | Sub-ms latency when data fits in RAM; network RTT (round-trip time) often dominates |
| **Not** | A full relational DB; no joins, limited query language; durability is optional/configurable |

**Sound bite:** “Redis is a networked in-memory dictionary of rich types with atomic ops, TTL, and pub/sub — not just a string cache.”

---

## B2. Learning Path (Base First)

1. **Keys, strings, TTL** — `GET`/`SET`, `EX`, `NX`, `INCR`
2. **Core types** — hash, set, sorted set (+ list/stream in [Queue](#part-ii--redis-queue))
3. **Patterns** — cache-aside, sessions, counters, dedup (`SET NX`), rate limits, locks
4. **Batching** — pipelines, transactions (`MULTI`/`EXEC`), Lua scripts
5. **Persistence & eviction** — RDB, AOF, `maxmemory` policies
6. **Scaling** — replication, Sentinel, Cluster, sharding keys
7. **Ops** — monitoring, `SLOWLOG`, memory, security
8. Then → **[Redis Queue](#part-ii--redis-queue)**

---

## B3. Keys & Naming

| Rule | Why |
|------|-----|
| Use namespaces: `user:42:profile`, `cache:product:99` | Avoid collisions; easy `SCAN` by prefix mentally |
| Prefer `:` or `/` as separators | Readable; Redis has no folders — prefixes are convention |
| Keep keys short but meaningful | Memory cost of millions of long keys adds up |
| Never use `KEYS *` in production | Blocks the server; use `SCAN` |
| Design for deletion / TTL | Orphan keys without expiry = memory leak |

```text
Good:  session:abc123
       ratelimit:ip:1.2.3.4:2026-09-15T19
       dedup:event:evt_9f3a

Bad:   userDataForTheProfileOfUserNumber42WithExtraStuff
       temp (no namespace, no TTL)
```

---

## B4. Data Types & Essential Commands

### B4.1 Strings

Binary-safe blobs; also used for ints/counters and JSON blobs.

| Command | Meaning | Example | Example explained | Python (`redis-py`) |
|---------|---------|---------|-------------------|---------------------|
| `SET key val [EX sec\|PX ms] [NX\|XX]` | Set; optional TTL; NX = only if missing; XX = only if exists | `SET session:abc 1 EX 3600 NX` | Create session key only if missing; auto-delete after 1 hour | `r.set("session:abc", 1, ex=3600, nx=True)` |
| `GET key` | Get value | `GET session:abc` | Read the value stored at `session:abc` (nil if missing) | `r.get("session:abc")` |
| `MGET` / `MSET` | Batch get/set | `MGET u:1 u:2` · `MSET u:1 Ada u:2 Grace` | Fetch two keys in one RTT · set two keys in one RTT | `r.mget("u:1", "u:2")` · `r.mset({"u:1": "Ada", "u:2": "Grace"})` |
| `INCR` / `DECR` / `INCRBY` | Atomic counter | `INCR visits` · `INCRBY score 10` | Bump `visits` by 1 · add 10 to `score` (creates key at 0 if new) | `r.incr("visits")` · `r.incrby("score", 10)` |
| `APPEND` / `STRLEN` / `GETRANGE` / `SETRANGE` | String ops | `APPEND log ":ok"` · `STRLEN greeting` · `GETRANGE k 0 4` | Append suffix · byte length · substring indices 0–4 inclusive | `r.append("log", ":ok")` · `r.strlen("greeting")` · `r.getrange("k", 0, 4)` |
| `GETDEL` / `GETEX` | Get + delete / get + set expiry (newer Redis) | `GETDEL temp:token` · `GETEX cache:p EX 60` | Return value then delete · return value and refresh TTL to 60s | `r.getdel("temp:token")` · `r.getex("cache:p", ex=60)` |

**Use for:** cache blobs, feature flags, distributed counters, locks (`SET … NX EX`), dedup markers.

### B4.2 Hashes

Field → value maps under one key. Great for objects.

| Command | Meaning | Example | Example explained | Python (`redis-py`) |
|---------|---------|---------|-------------------|---------------------|
| `HSET key field val [field val …]` | Set field(s) | `HSET user:1 name Ada role admin` | Store two fields on hash `user:1` in one command | `r.hset("user:1", mapping={"name": "Ada", "role": "admin"})` |
| `HGET` / `HMGET` / `HGETALL` | Read field(s) / all | `HGET user:1 name` · `HGETALL user:1` | One field · every field/value pair on the hash | `r.hget("user:1", "name")` · `r.hgetall("user:1")` |
| `HDEL` / `HEXISTS` / `HLEN` | Delete / exists / count | `HDEL user:1 role` · `HEXISTS user:1 name` · `HLEN user:1` | Remove `role` · 1 if `name` exists · number of fields | `r.hdel("user:1", "role")` · `r.hexists("user:1", "name")` · `r.hlen("user:1")` |
| `HINCRBY` | Atomic field counter | `HINCRBY user:1 login_count 1` | Increment hash field `login_count` by 1 | `r.hincrby("user:1", "login_count", 1)` |
| `HSCAN` | Iterate fields safely | `HSCAN user:1 0 MATCH n* COUNT 10` | Cursor-iterate fields starting at 0; match `n*`; hint ~10 | `r.hscan("user:1", 0, match="n*", count=10)` |

**Use for:** user profiles, shopping carts, config maps. Prefer hash over many `user:42:name` string keys when fields share TTL/lifecycle.

### B4.3 Sets

Unordered unique members.

| Command | Meaning | Example | Example explained | Python (`redis-py`) |
|---------|---------|---------|-------------------|---------------------|
| `SADD` / `SREM` | Add / remove | `SADD tags:post:1 redis go` · `SREM tags:post:1 go` | Tag post with `redis` and `go` · remove `go` | `r.sadd("tags:post:1", "redis", "go")` · `r.srem("tags:post:1", "go")` |
| `SISMEMBER` / `SMEMBERS` / `SCARD` | Membership / all / count | `SISMEMBER online u42` · `SMEMBERS tags:post:1` · `SCARD online` | Is `u42` online? · list all tags · how many online | `r.sismember("online", "u42")` · `r.smembers("tags:post:1")` · `r.scard("online")` |
| `SINTER` / `SUNION` / `SDIFF` | Set algebra | `SINTER tags:a tags:b` · `SUNION a b` · `SDIFF a b` | Shared members · all members · in `a` but not `b` | `r.sinter("tags:a", "tags:b")` · `r.sunion("a", "b")` · `r.sdiff("a", "b")` |
| `SPOP` / `SRANDMEMBER` | Random | `SPOP lottery` · `SRANDMEMBER online 3` | Remove+return one random winner · sample 3 without removing | `r.spop("lottery")` · `r.srandmember("online", 3)` |
| `SSCAN` | Iterate | `SSCAN online 0 MATCH u* COUNT 100` | Cursor-scan online users whose ids start with `u` | `r.sscan("online", 0, match="u*", count=100)` |

**Use for:** tags, unique visitors, ACL groups, “users online”.

### B4.4 Sorted Sets (ZSets)

Unique members with a **score** (sorted by score).

| Command | Meaning | Example | Example explained | Python (`redis-py`) |
|---------|---------|---------|-------------------|---------------------|
| `ZADD key score member` | Add / update score | `ZADD leaderboard 1500 ada 2200 grace` | Put `ada` at 1500 and `grace` at 2200 on the board | `r.zadd("leaderboard", {"ada": 1500, "grace": 2200})` |
| `ZRANGE` / `ZREVRANGE` | By rank | `ZRANGE leaderboard 0 9 WITHSCORES` · `ZREVRANGE leaderboard 0 9` | Lowest 10 + scores · highest 10 (top of board) | `r.zrange("leaderboard", 0, 9, withscores=True)` · `r.zrevrange("leaderboard", 0, 9)` |
| `ZRANGEBYSCORE` / `ZREVRANGEBYSCORE` | By score | `ZRANGEBYSCORE delay 0 1700000000` | Members with score in `[0, 1700000000]` (e.g. due jobs) | `r.zrangebyscore("delay", 0, 1700000000)` |
| `ZRANK` / `ZSCORE` | Rank / score of member | `ZREVRANK leaderboard ada` · `ZSCORE leaderboard ada` | 0-based rank from the top · ada’s numeric score | `r.zrevrank("leaderboard", "ada")` · `r.zscore("leaderboard", "ada")` |
| `ZREM` / `ZCARD` / `ZCOUNT` | Remove / size / count in range | `ZREM leaderboard bob` · `ZCARD leaderboard` · `ZCOUNT lb 1000 2000` | Drop bob · total players · how many scored 1000–2000 | `r.zrem("leaderboard", "bob")` · `r.zcard("leaderboard")` · `r.zcount("lb", 1000, 2000)` |
| `ZINCRBY` | Bump score | `ZINCRBY leaderboard 50 ada` | Add 50 points to ada (creates member if missing) | `r.zincrby("leaderboard", 50, "ada")` |
| `ZPOPMIN` / `ZPOPMAX` | Pop lowest / highest | `ZPOPMIN delay 1` · `ZPOPMAX leaderboard 1` | Take next due job · take current #1 and remove them | `r.zpopmin("delay", 1)` · `r.zpopmax("leaderboard", 1)` |

**Use for (Base):** leaderboards, time-ordered indexes, rankings.  
**Queue uses** (delay / priority): see [Q4](#q4-delay--priority-queues-zsets).

### B4.5 Other Types (Know They Exist)

| Type | Role | Example | Example explained | Python (`redis-py`) |
|------|------|---------|-------------------|---------------------|
| **Bitmap** | Bit ops on strings — analytics flags | `SETBIT dau:2026-09-15 42 1` · `BITCOUNT dau:2026-09-15` | Mark user offset 42 active today · count set bits (≈ DAU) | `r.setbit("dau:2026-09-15", 42, 1)` · `r.bitcount("dau:2026-09-15")` |
| **Bitfield** | Packed integers | `BITFIELD flags INCRBY u8 #0 1 GET u8 #0` | Bump unsigned-8 at index 0 by 1, then read it | `r.bitfield("flags").incrby("u8", "#0", 1).get("u8", "#0").execute()` |
| **HyperLogLog** | Approx unique counts — tiny memory | `PFADD uniques u1 u2` · `PFCOUNT uniques` | Observe two ids · approximate distinct count | `r.pfadd("uniques", "u1", "u2")` · `r.pfcount("uniques")` |
| **Geo** | Geo indexes on zsets | `GEOADD places 77.59 12.97 blr` · `GEOSEARCH places FROMLONLAT 77.6 13.0 BYRADIUS 5 km` | Store Bangalore lon/lat · find places within 5 km | `r.geoadd("places", (77.59, 12.97, "blr"))` · `r.geosearch("places", longitude=77.6, latitude=13.0, radius=5, unit="km")` |
| **JSON** (Redis Stack / module) | Document ops | `JSON.SET user:1 $ '{"name":"Ada"}'` · `JSON.GET user:1 $.name` | Write JSON doc at root · read `name` path | `r.json().set("user:1", "$", {"name": "Ada"})` · `r.json().get("user:1", "$.name")` |
| **Bloom / Search / TimeSeries** | Via Redis Stack / modules | `BF.ADD seen url1` · `TS.ADD temp 1710000000 22.5` | Add to bloom filter · append temperature sample | `r.bf().add("seen", "url1")` · `r.ts().add("temp", 1710000000, 22.5)` |

**Lists & Streams** live in [Part II — Redis Queue](#part-ii--redis-queue).

---

## B5. TTL, Expiry & Key Lifecycle

| Command | Meaning | Example | Example explained | Python (`redis-py`) |
|---------|---------|---------|-------------------|---------------------|
| `EXPIRE key sec` / `PEXPIRE` | Set TTL | `EXPIRE session:abc 3600` · `PEXPIRE token 5000` | Expire in 3600s · expire in 5000ms | `r.expire("session:abc", 3600)` · `r.pexpire("token", 5000)` |
| `TTL` / `PTTL` | Remaining TTL (-1 = no expiry, -2 = missing) | `TTL session:abc` · `PTTL token` | Seconds left · milliseconds left | `r.ttl("session:abc")` · `r.pttl("token")` |
| `PERSIST key` | Remove TTL | `PERSIST session:abc` | Make the key live forever (until deleted) | `r.persist("session:abc")` |
| `SET … EX` / `SET … PX` | Set value + TTL atomically | `SET cache:p '{"id":1}' EX 300` · `SET lock:x 1 PX 5000 NX` | Cache JSON for 5 min · take lock for 5s only if free | `r.set("cache:p", '{"id":1}', ex=300)` · `r.set("lock:x", 1, px=5000, nx=True)` |
| `EXPIREAT` / `PEXPIREAT` | Expire at unix time | `EXPIREAT promo 1735689600` | Delete `promo` at that unix timestamp | `r.expireat("promo", 1735689600)` |

**Rules of thumb:**
- Always TTL cache keys and ephemeral markers (sessions, dedup, rate-limit windows).
- Updating a key with `SET` **replaces** the value; TTL behavior depends on options (`KEEPTTL` on modern Redis).
- Expired keys are deleted lazily / via active expiry — don’t assume instant free memory.

---

## B6. Generic Key Commands

| Command | Meaning | Example | Example explained | Python (`redis-py`) |
|---------|---------|---------|-------------------|---------------------|
| `EXISTS key` | 1/0 | `EXISTS session:abc` | Returns 1 if key exists, else 0 | `r.exists("session:abc")` |
| `DEL` / `UNLINK` | Delete (UNLINK async-ish for big values) | `DEL cache:p` · `UNLINK big:blob` | Sync delete · reclaim big value in background | `r.delete("cache:p")` · `r.unlink("big:blob")` |
| `TYPE key` | Type name | `TYPE leaderboard` → `zset` | Reports the Redis type of that key | `r.type("leaderboard")` |
| `RENAME` / `RENAMENX` | Rename | `RENAME temp:v1 live:v1` · `RENAMENX a b` | Overwrite rename · rename only if `b` does not exist | `r.rename("temp:v1", "live:v1")` · `r.renamenx("a", "b")` |
| `SCAN cursor [MATCH pat] [COUNT n]` | Cursor iterate — **production safe** | `SCAN 0 MATCH cache:* COUNT 100` | Start scan; next batch of `cache:*` keys (use returned cursor) | `r.scan(0, match="cache:*", count=100)` |
| `DBSIZE` | Key count (approx lifecycle awareness) | `DBSIZE` | Number of keys in current DB | `r.dbsize()` |
| `FLUSHDB` / `FLUSHALL` | Wipe — **never** on shared prod | `FLUSHDB` (local/dev only) | Delete all keys in this DB (destructive) | `r.flushdb()` |

---

## B7. Atomic Patterns (Non-Queue)

### B7.1 Cache-aside

```text
1. GET cache:key
2. miss → load DB → SET cache:key value EX ttl
3. on write → update DB → DEL cache:key (or SET fresh)
```

### B7.2 Dedup / idempotency (`SET NX`)

```text
SET dedup:<id> 1 NX EX 86400
→ OK  = first time → process
→ nil = duplicate → skip
```

See repo: `concepts/system-design/dedup/4_redis/main.go`.

### B7.3 Distributed lock (basic)

```text
SET lock:resource <unique_token> NX EX 30
… work …
# release only if token matches (Lua or GET + compare + DEL carefully)
```

Prefer **Redlock** / library locks for multi-node; simple `SET NX` is single-instance only.

### B7.4 Rate limiting (fixed window)

```text
INCR ratelimit:<user>:<window>
EXPIRE … (only on first increment)
if count > N → reject
```

Better variants: sliding window (zset of timestamps), token bucket (Lua).

### B7.5 Leaderboard

```text
ZADD leaderboard <score> <user>
ZREVRANGE leaderboard 0 9 WITHSCORES   # top 10
ZRANK / ZREVRANK                        # user rank
```

Queue / messaging patterns → [Part II](#part-ii--redis-queue).

---

## B8. Pipelines, Transactions, Lua

| Tool | What it gives you | Limitation |
|------|-------------------|------------|
| **Pipeline** | Batch commands; fewer RTTs | Not atomic across commands |
| **`MULTI`/`EXEC`** | Queued commands run as one unit | Not rollback on logic errors; watches for optimism |
| **`WATCH` keys`** | Optimistic concurrency | Retry on conflict |
| **Lua `EVAL`** | Server-side atomic multi-step logic | Keep scripts short; avoid big scans |

**When to use Lua:** compare-and-delete lock release, sliding-window rate limit, multi-key invariants that must not interleave.

```text
-- release lock only if token matches
if redis.call("GET", KEYS[1]) == ARGV[1] then
  return redis.call("DEL", KEYS[1])
else
  return 0
end
```

---

## B9. Persistence & Durability

| Mode | Mechanism | Tradeoff |
|------|-----------|----------|
| **RDB** | Periodic snapshots | Fast restarts; can lose data since last save |
| **AOF** | Append every write | More durable; larger / slower; `everysec` common |
| **RDB + AOF** | Combined | Typical production compromise |
| **No persistence** | Pure cache | Fine if data is rebuildable |

**Interview:** Redis can be durable, but default mental model for cache is “ok to lose.” Tune AOF/RDB to the use case (session store ≠ analytics buffer).

---

## B10. Memory & Eviction

When `maxmemory` is hit, Redis evicts per policy:

| Policy | Behavior |
|--------|----------|
| `noeviction` | Writes error when full |
| `allkeys-lru` | Evict least recently used (any key) — **common for cache** |
| `volatile-lru` | LRU among keys **with TTL** |
| `allkeys-lfu` / `volatile-lfu` | Least frequently used |
| `allkeys-random` / `volatile-random` | Random |
| `volatile-ttl` | Evict soonest-to-expire |

**Also learn:**
- Big values vs many small keys
- `MEMORY USAGE key`, `INFO memory`
- Avoid storing huge blobs if a CDN/object store fits better

---

## B11. Replication, HA, Clustering

```text
Clients
   │
   ▼
┌─────────┐     async repl      ┌─────────┐
│ Primary │ ──────────────────► │ Replica │  (read scaling / failover source)
└─────────┘                     └─────────┘
```

| Topic | Learn |
|-------|--------|
| **Replica** | Async by default → possible lag / lost writes on failover |
| **Sentinel** | Monitors primary; promotes replica on failure |
| **Cluster** | Data sharded across 16384 hash slots; multi-node |
| **Hash tags** | `{user:42}.profile` and `{user:42}.cart` → same slot (multi-key ops) |
| **Cross-slot** | Multi-key commands fail if keys not same slot |

**Sound bite:** “Replication = HA/read scale; Cluster = horizontal partition of the keyspace.”

---

## B12. Consistency & Failure Modes

| Reality | Implication |
|---------|-------------|
| Single instance: commands atomic | Race-free *inside* one Redis op |
| Multi-key without Lua/MULTI | Interleaving possible across clients |
| Replica lag | Stale reads if you read replicas |
| Network partition / failover | Brief unavailability; possible write loss (async repl) |
| Redis down | Cache: fail open/closed; locks/dedup: define policy explicitly |

**Fail-open vs fail-closed** (from your dedup notes): analytics often process on Redis error; payments often reject/skip until Redis is back.

---

## B13. Security & Ops Basics

| Topic | Practice |
|-------|----------|
| Bind / network | Never expose `6379` to the public internet |
| `AUTH` / ACLs | Password + least-privilege users (Redis 6+) |
| TLS | Encrypt in transit in cloud/prod |
| Dangerous commands | Rename/disable `FLUSHALL`, `KEYS`, `CONFIG` in prod |
| Monitoring | `INFO`, latency, hit rate, evictions, connected clients |
| `SLOWLOG` | Find expensive commands |
| Keystorms | Hot keys / big keys — shard or redesign |

---

## B14. CLI Quick Reference

```bash
docker run -d --name redis -p 6379:6379 redis:alpine
redis-cli
redis-cli -h host -p 6379 -a password

PING
INFO server
INFO memory
MONITOR          # debug only — very noisy
SLOWLOG GET 10
CLIENT LIST
```

Useful interactive:
```text
SET greeting "hello" EX 60
GET greeting
TTL greeting
HSET user:1 name Ada role admin
HGETALL user:1
ZADD scores 100 ada 200 grace
ZREVRANGE scores 0 -1 WITHSCORES
```

---

## B15. Client Libraries (Mental Model)

| Language | Common client |
|----------|----------------|
| Go | `github.com/redis/go-redis/v9` |
| Python | `redis-py` |
| Node | `node-redis` / `ioredis` |
| Java | Lettuce / Jedis |

Always set: timeouts, connection pool size, and retry/circuit-breaker policy around Redis as a dependency.

---

## B16. Redis vs Memcached vs DB

| Need | Prefer |
|------|--------|
| Rich types, TTL, pub/sub, streams, Lua | **Redis** |
| Simple distributed string cache, huge horizontal scale | Memcached (sometimes) |
| Complex queries, strong multi-row transactions, relations | Primary DB |
| Huge durable blobs | Object storage + cache pointer in Redis |

---

## B17. Interview Checklist (Base)

- [ ] Explain Redis in one sentence + when *not* to use it  
- [ ] Name core data types and one use case each  
- [ ] `SET NX EX` for locks / dedup  
- [ ] Cache-aside vs write-through (see caching cheatsheet folder)  
- [ ] TTL + eviction policies  
- [ ] Pipeline vs MULTI vs Lua  
- [ ] RDB vs AOF  
- [ ] Primary/replica vs Cluster  
- [ ] Why `KEYS` is dangerous; use `SCAN`  
- [ ] Hot key / big key problems  

---

## B18. Practice Exercises (Base)

1. Cache a DB row with TTL; invalidate on update.  
2. Idempotent webhook handler with `SET NX EX`.  
3. Fixed-window and sliding-window rate limiter.  
4. Leaderboard with `ZINCRBY` + top-N query.  
5. Unique daily active users with a set or HyperLogLog.  
6. Lock with token + Lua release.  
7. Point `go-redis` at Docker Redis and replace the mock in `4_redis/main.go`.

---

## B19. Official Resources

- Docs: [redis.io/docs](https://redis.io/docs/)  
- Commands: [redis.io/commands](https://redis.io/commands/)  
- Sandbox: [redis.io/try/sandbox](https://redis.io/try/sandbox/)  
- University: [university.redis.io](https://university.redis.io/)  

---

# Part II — Redis Queue

Use Redis as a **message broker / job queue**: list queues, Streams (ack + consumer groups), pub/sub, and delay/priority queues with sorted sets.

---

## Q1. Which Queue Tool When?

| Need | Prefer | Why |
|------|--------|-----|
| Simplest FIFO job queue | **Lists** (`LPUSH` + `BRPOP`) | Tiny API; no ack/replay |
| Ack, retry, multiple consumers, backlog | **Streams** + consumer groups | Kafka-lite; durable-ish log |
| Fire-and-forget fan-out (live only) | **Pub/Sub** | No persistence; no replay |
| Run later / priority | **ZSet** (score = time or priority) | Pop with `ZPOPMIN` / range-by-score |
| Heavy reliable broker features | Kafka / SQS / RabbitMQ | Redis queues are “good enough,” not full brokers |

---

## Q2. List Queues

Ordered sequences (linked-list-ish). Push/pop either end — the classic Redis job queue.

| Command | Meaning | Example | Example explained | Python (`redis-py`) |
|---------|---------|---------|-------------------|---------------------|
| `LPUSH` / `RPUSH` | Push left / right | `LPUSH jobs '{"id":1}'` · `RPUSH feed evt1` | Push job onto head of queue · append event to feed tail | `r.lpush("jobs", '{"id":1}')` · `r.rpush("feed", "evt1")` |
| `LPOP` / `RPOP` | Pop left / right | `LPOP jobs` · `RPOP feed` | Dequeue from head · remove last feed item | `r.lpop("jobs")` · `r.rpop("feed")` |
| `LRANGE key start stop` | Slice (0 = first, -1 = last) | `LRANGE feed 0 9` · `LRANGE feed 0 -1` | First 10 items · entire list | `r.lrange("feed", 0, 9)` · `r.lrange("feed", 0, -1)` |
| `LLEN` / `LINDEX` / `LTRIM` | Length / index / trim | `LLEN jobs` · `LINDEX feed 0` · `LTRIM feed 0 99` | Queue depth · peek index 0 · keep only newest 100 | `r.llen("jobs")` · `r.lindex("feed", 0)` · `r.ltrim("feed", 0, 99)` |
| `BLPOP` / `BRPOP` | Blocking pop (simple queue) | `BRPOP jobs 0` · `BLPOP jobs 5` | Block forever for a job · wait up to 5s then return nil | `r.brpop("jobs", timeout=0)` · `r.blpop("jobs", timeout=5)` |

### Q2.1 Simple FIFO queue pattern

```text
producer: LPUSH jobs <payload>
consumer: BRPOP jobs 0
```

```python
# producer
r.lpush("jobs", '{"id": 1, "type": "email"}')

# consumer (blocks until a job arrives)
queue, payload = r.brpop("jobs", timeout=0)
```

**Limits:** no ack — if the worker dies after `BRPOP`, the job is gone. No native multi-consumer fair share. For reliability → Streams.

**Also useful:** recent activity feeds, capped logs (`LTRIM`).

---

## Q3. Streams (Reliable Job / Event Log)

Append-only log with **consumer groups** (Kafka-lite). Best Redis queue when you need ack + retry.

| Command | Meaning | Example | Example explained | Python (`redis-py`) |
|---------|---------|---------|-------------------|---------------------|
| `XADD stream * field val …` | Append entry (`*` = auto ID) | `XADD events * type click user u42` | Append event with auto ID; fields `type`/`user` | `r.xadd("events", {"type": "click", "user": "u42"})` |
| `XREAD` / `XREADGROUP` | Read / consumer-group read | `XREAD COUNT 10 STREAMS events 0` · `XREADGROUP GROUP g c COUNT 1 STREAMS events >` | Read up to 10 from start · consumer `c` in group `g` gets next new (`>`) | `r.xread(streams={"events": "0"}, count=10)` · `r.xreadgroup("g", "c", {"events": ">"}, count=1)` |
| `XGROUP CREATE` | Create consumer group | `XGROUP CREATE events workers $ MKSTREAM` | Group `workers` starts at latest (`$`); create stream if missing | `r.xgroup_create("events", "workers", id="$", mkstream=True)` |
| `XACK` | Acknowledge processing | `XACK events workers 1710000000000-0` | Mark message ID as done for group `workers` | `r.xack("events", "workers", "1710000000000-0")` |
| `XRANGE` / `XLEN` / `XTRIM` | Range / length / trim | `XRANGE events - + COUNT 10` · `XLEN events` · `XTRIM events MAXLEN ~ 10000` | First ~10 entries · entry count · approx keep last 10k | `r.xrange("events", count=10)` · `r.xlen("events")` · `r.xtrim("events", maxlen=10000, approximate=True)` |

### Q3.1 Consumer-group job flow

```text
1. XGROUP CREATE jobs workers $ MKSTREAM
2. producer: XADD jobs * type email to user@x.com
3. worker:   XREADGROUP GROUP workers w1 COUNT 1 STREAMS jobs >
4. process payload
5. XACK jobs workers <id>          # success
6. on crash: pending entries stay in PEL → claim/retry (XCLAIM / XAUTOCLAIM)
```

```python
r.xgroup_create("jobs", "workers", id="$", mkstream=True)
r.xadd("jobs", {"type": "email", "to": "user@x.com"})

msgs = r.xreadgroup("workers", "w1", {"jobs": ">"}, count=1, block=5000)
# process…
# r.xack("jobs", "workers", msg_id)
```

**Use for:** event sourcing lite, job queues with ack, activity streams, multi-worker fan-out with at-least-once delivery.

---

## Q4. Delay & Priority Queues (ZSets)

Reuse sorted sets from Base: **score = unix timestamp** (delay) or **priority** (lower = sooner).

```text
# schedule job for later
ZADD delayed <run_at_unix> <job_payload>

# worker poll
ZRANGEBYSCORE delayed -inf <now> LIMIT 0 1
# or atomically:
ZPOPMIN delayed 1   # if score <= now, process; else put back / sleep
```

```python
import time
run_at = time.time() + 60
r.zadd("delayed", {"job:42": run_at})

due = r.zrangebyscore("delayed", "-inf", time.time(), start=0, num=1)
```

**Priority queue:** `ZADD pq <priority> <job>` then `ZPOPMIN pq`.

---

## Q5. Pub/Sub (Not a Durable Queue)

| Command | Meaning | Example | Example explained | Python (`redis-py`) |
|---------|---------|---------|-------------------|---------------------|
| `PUBLISH channel msg` | Fire-and-forget broadcast | `PUBLISH notifications "user:42 signed in"` | Send message to all current `notifications` subscribers | `r.publish("notifications", "user:42 signed in")` |
| `SUBSCRIBE` / `PSUBSCRIBE` | Listen | `SUBSCRIBE notifications` · `PSUBSCRIBE notif*` | Listen on one channel · listen on all channels matching `notif*` | `p = r.pubsub(); p.subscribe("notifications")` · `p.psubscribe("notif*")` |

**Caveat:** no persistence, no replay; offline subscribers miss messages; slow subscribers can drop. Prefer **Streams** when you need durability or catch-up.

**Use for:** live UI notifications, cache invalidation broadcasts, “someone is typing” signals.

---

## Q6. Queue Design Checklist

| Topic | Practice |
|-------|----------|
| Payload size | Keep small; store big blobs in S3/DB and put an id in the queue |
| Idempotency | Workers should tolerate at-least-once delivery (`SET NX` dedup from Base) |
| Poison messages | Cap retries; dead-letter list/stream for failures |
| Backpressure | Monitor `LLEN` / `XLEN`; alert before memory blows up |
| Visibility | Streams PEL + `XCLAIM`; lists have no built-in lease |
| Trim | `XTRIM` / `LTRIM` so queues don’t grow forever |

---

## Q7. Interview Checklist (Queue)

- [ ] List queue (`LPUSH`/`BRPOP`) vs Streams vs Pub/Sub  
- [ ] Why list queues lose jobs on worker crash  
- [ ] Consumer groups + `XACK` + pending entries  
- [ ] Delay queue with zset scores  
- [ ] When to leave Redis for Kafka/SQS  

---

## Q8. Practice Exercises (Queue)

1. Build a list-based email queue (`LPUSH` / `BRPOP`).  
2. Redo it with Streams + consumer group + `XACK`.  
3. Add a delay queue with a zset (`run_at` score).  
4. Pub/Sub cache-bust channel; contrast with Stream replay.  
5. Simulate worker crash: show list job loss vs Stream pending recovery.  
