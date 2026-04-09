/**
 * SLIDING WINDOW LOG ALGORITHM
 *
 * Concept: Keep a log (sorted list) of timestamps for every request within
 * the last N seconds. On each new request, evict timestamps older than the
 * window, then check if the remaining log count is below the limit.
 *
 * This is the most accurate rate limiting algorithm — it eliminates the
 * boundary spike problem entirely. However it is the most memory-intensive:
 * O(limit) entries per key. Under heavy load with high limits, this can
 * consume significant memory.
 *
 * Time complexity: O(log n) amortized (binary-search eviction) or O(k)
 *                  where k = entries evicted per call
 * Space complexity: O(limit) per key
 */

class Mutex {
  private queue: Array<() => void> = [];
  private locked = false;

  async acquire(): Promise<void> {
    if (!this.locked) { this.locked = true; return; }
    return new Promise((resolve) => this.queue.push(resolve));
  }

  release(): void {
    const next = this.queue.shift();
    if (next) next(); else this.locked = false;
  }
}

export class SlidingWindowLogRateLimiter {
  // Each key maps to a sorted array of request timestamps (ascending)
  private logs: Map<string, number[]> = new Map();
  private mutexes: Map<string, Mutex> = new Map();

  constructor(
    private readonly limit: number,       // max requests in the window
    private readonly windowMs: number     // sliding window size in ms
  ) {}

  private getMutex(key: string): Mutex {
    if (!this.mutexes.has(key)) this.mutexes.set(key, new Mutex());
    return this.mutexes.get(key)!;
  }

  /**
   * Binary search to find the first index whose timestamp is >= cutoff.
   * Everything before that index is older than the window and can be evicted.
   */
  private lowerBound(timestamps: number[], cutoff: number): number {
    let lo = 0, hi = timestamps.length;
    while (lo < hi) {
      const mid = (lo + hi) >>> 1;
      if (timestamps[mid] < cutoff) lo = mid + 1;
      else hi = mid;
    }
    return lo;
  }

  /**
   * CONCURRENCY NOTE: Two concurrent requests at the same timestamp could
   * both read log.length < limit and both append — exceeding the limit by 1.
   * The mutex prevents this by serialising the read-then-write sequence.
   *
   * In distributed systems (Redis), you'd use a Lua script or MULTI/EXEC
   * to make ZADD + ZCOUNT atomic.
   */
  async allowRequest(key: string): Promise<{
    allowed: boolean;
    remaining: number;
    oldestRequestMs: number | null;
  }> {
    const mutex = this.getMutex(key);
    await mutex.acquire();

    try {
      const now = Date.now();
      const cutoff = now - this.windowMs;

      if (!this.logs.has(key)) this.logs.set(key, []);
      const log = this.logs.get(key)!;

      // Evict timestamps that have slid out of the window
      const evictBefore = this.lowerBound(log, cutoff);
      if (evictBefore > 0) {
        log.splice(0, evictBefore);
      }

      if (log.length >= this.limit) {
        const oldestRequestMs = log[0] ?? null;
        return { allowed: false, remaining: 0, oldestRequestMs };
      }

      // Record this request's timestamp
      log.push(now);

      return {
        allowed: true,
        remaining: this.limit - log.length,
        oldestRequestMs: log[0] ?? null,
      };
    } finally {
      mutex.release();
    }
  }

  /**
   * How long (ms) until the oldest in-window request slides out,
   * freeing up one slot. Returns 0 if slots are already available.
   */
  async msUntilNextSlot(key: string): Promise<number> {
    const mutex = this.getMutex(key);
    await mutex.acquire();

    try {
      const now = Date.now();
      const cutoff = now - this.windowMs;
      const log = this.logs.get(key);

      if (!log || log.length === 0) return 0;

      // Evict stale entries first
      const evictBefore = this.lowerBound(log, cutoff);
      if (evictBefore > 0) log.splice(0, evictBefore);

      if (log.length < this.limit) return 0;

      // Oldest entry in window; it will slide out at oldest + windowMs
      return Math.max(0, log[0] + this.windowMs - now);
    } finally {
      mutex.release();
    }
  }
}

// ---------------------------------------------------------------------------
// Demo — shows no boundary spike unlike Fixed Window
// ---------------------------------------------------------------------------
async function demo() {
  console.log("=== Sliding Window Log Demo ===");
  console.log("Config: limit=5 requests per 1 second window\n");

  const limiter = new SlidingWindowLogRateLimiter(5, 1000);

  // Rapid burst — only 5 pass
  for (let i = 1; i <= 7; i++) {
    const res = await limiter.allowRequest("user:alice");
    console.log(
      `Request ${i}: ${res.allowed ? "ALLOWED" : "REJECTED"} | remaining=${res.remaining}`
    );
  }

  const waitMs = await limiter.msUntilNextSlot("user:alice");
  console.log(`\nNext slot available in ~${waitMs}ms`);

  // Wait for the oldest request to slide out of the window
  await new Promise((r) => setTimeout(r, waitMs + 10));

  console.log("\nAfter oldest request slides out:");
  const res = await limiter.allowRequest("user:alice");
  console.log(`Request 8: ${res.allowed ? "ALLOWED" : "REJECTED"}`);

  // No boundary spike demo
  console.log("\n--- No Boundary Spike (vs Fixed Window) ---");
  const limiter2 = new SlidingWindowLogRateLimiter(5, 1000);

  // Pack 5 requests near "end of window" by using them up now
  for (let i = 0; i < 5; i++) await limiter2.allowRequest("spike-check");

  // Wait 600ms — in Fixed Window this would reset; here the window SLIDES
  await new Promise((r) => setTimeout(r, 600));

  // These timestamps are only 600ms old, window is 1000ms — still counted
  const extraReq = await limiter2.allowRequest("spike-check");
  console.log(`Request after 600ms (still in sliding window): ${extraReq.allowed ? "ALLOWED" : "REJECTED (correct!)"}`);

  // Concurrent stress test
  console.log("\n--- 20 simultaneous requests (limit=5) ---");
  const limiter3 = new SlidingWindowLogRateLimiter(5, 2000);
  const results = await Promise.all(
    Array.from({ length: 20 }, (_, i) =>
      limiter3.allowRequest("user:concurrent").then((r) => `R${i + 1}:${r.allowed ? "OK" : "NO"}`)
    )
  );
  const allowed = results.filter((r) => r.includes("OK")).length;
  console.log(`Allowed: ${allowed}/20 (should be exactly 5)`);
}

demo();
