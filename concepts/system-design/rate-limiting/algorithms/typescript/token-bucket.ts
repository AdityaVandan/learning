/**
 * TOKEN BUCKET ALGORITHM
 *
 * Concept: A bucket holds tokens up to a max capacity. Tokens are added at a
 * fixed refill rate. Each incoming request consumes one (or more) tokens.
 * If the bucket has enough tokens, the request is allowed; otherwise rejected.
 *
 * Allows short bursts (up to bucket capacity) while maintaining a steady
 * average throughput equal to the refill rate.
 *
 * Time complexity: O(1) per request
 * Space complexity: O(1) per user/key
 */

interface TokenBucketState {
  tokens: number;
  lastRefillTime: number; // epoch ms
}

// A minimal async mutex to prevent race conditions when multiple async
// operations check-and-update the same bucket state concurrently.
class Mutex {
  private queue: Array<() => void> = [];
  private locked = false;

  async acquire(): Promise<void> {
    if (!this.locked) {
      this.locked = true;
      return;
    }
    return new Promise((resolve) => this.queue.push(resolve));
  }

  release(): void {
    const next = this.queue.shift();
    if (next) {
      next();
    } else {
      this.locked = false;
    }
  }
}

export class TokenBucketRateLimiter {
  private buckets: Map<string, TokenBucketState> = new Map();
  private mutexes: Map<string, Mutex> = new Map();

  constructor(
    private readonly capacity: number,      // max tokens in bucket
    private readonly refillRate: number,    // tokens added per second
  ) {}

  private getMutex(key: string): Mutex {
    if (!this.mutexes.has(key)) {
      this.mutexes.set(key, new Mutex());
    }
    return this.mutexes.get(key)!;
  }

  private refill(state: TokenBucketState, now: number): void {
    const elapsedSeconds = (now - state.lastRefillTime) / 1000;
    const tokensToAdd = elapsedSeconds * this.refillRate;

    // Cap tokens at capacity — excess tokens are lost (unlike leaky bucket)
    state.tokens = Math.min(this.capacity, state.tokens + tokensToAdd);
    state.lastRefillTime = now;
  }

  /**
   * Try to consume `tokensRequired` tokens for the given key.
   *
   * CONCURRENCY NOTE: The mutex ensures that between the refill calculation
   * and the token deduction, no other async operation can interleave and
   * read a stale token count. Without this, two concurrent requests could
   * both see "1 token available" and both succeed, causing over-counting.
   */
  async allowRequest(key: string, tokensRequired = 1): Promise<boolean> {
    const mutex = this.getMutex(key);
    await mutex.acquire();

    try {
      const now = Date.now();

      if (!this.buckets.has(key)) {
        // New key: start with a full bucket
        this.buckets.set(key, { tokens: this.capacity, lastRefillTime: now });
      }

      const state = this.buckets.get(key)!;
      this.refill(state, now);

      if (state.tokens >= tokensRequired) {
        state.tokens -= tokensRequired;
        return true; // allowed
      }

      return false; // rejected
    } finally {
      mutex.release();
    }
  }

  /** Returns remaining tokens and time until next token (ms). */
  async getStatus(key: string): Promise<{ tokens: number; msUntilNextToken: number }> {
    const mutex = this.getMutex(key);
    await mutex.acquire();

    try {
      const now = Date.now();
      if (!this.buckets.has(key)) {
        return { tokens: this.capacity, msUntilNextToken: 0 };
      }

      const state = this.buckets.get(key)!;
      this.refill(state, now);

      const msUntilNextToken = state.tokens >= 1
        ? 0
        : Math.ceil((1 - (state.tokens % 1)) / this.refillRate * 1000);

      return { tokens: Math.floor(state.tokens), msUntilNextToken };
    } finally {
      mutex.release();
    }
  }
}

// ---------------------------------------------------------------------------
// Demo
// ---------------------------------------------------------------------------
async function demo() {
  // 5 token capacity, refill 2 tokens/second
  const limiter = new TokenBucketRateLimiter(5, 2);

  console.log("=== Token Bucket Demo ===");
  console.log("Config: capacity=5, refillRate=2 tokens/sec\n");

  // Simulate 7 rapid requests — only first 5 should pass
  for (let i = 1; i <= 7; i++) {
    const allowed = await limiter.allowRequest("user:alice");
    console.log(`Request ${i}: ${allowed ? "ALLOWED" : "REJECTED"}`);
  }

  // Wait 1 second — 2 new tokens should be available
  console.log("\nWaiting 1 second for refill...\n");
  await new Promise((r) => setTimeout(r, 1000));

  for (let i = 8; i <= 10; i++) {
    const allowed = await limiter.allowRequest("user:alice");
    console.log(`Request ${i}: ${allowed ? "ALLOWED" : "REJECTED"}`);
  }

  // Concurrency stress test — 10 requests fired simultaneously
  console.log("\n--- Concurrent requests (10 simultaneous) ---");
  const limiter2 = new TokenBucketRateLimiter(3, 1);
  const results = await Promise.all(
    Array.from({ length: 10 }, (_, i) =>
      limiter2.allowRequest("user:bob").then((ok) => `Req${i + 1}:${ok ? "OK" : "NO"}`)
    )
  );
  console.log(results.join("  "));
  // Exactly 3 should be OK (bucket capacity = 3)
}

demo();
