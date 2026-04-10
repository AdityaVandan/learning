/**
 * SLIDING WINDOW COUNTER (HYBRID) ALGORITHM
 *
 * Concept: A weighted approximation of a true sliding window that uses only
 * two fixed-window counters — the current window and the previous window.
 *
 * Formula:
 *   estimated_count = prev_count × (1 - elapsed_fraction) + curr_count
 *
 * Where `elapsed_fraction` = how far we are through the current window (0.0–1.0).
 *
 * Example: limit=100, window=60s
 *   prev window: 80 requests
 *   current window: 30 requests, 40s elapsed (fraction = 40/60 ≈ 0.667)
 *   estimate = 80 × (1 - 0.667) + 30 = 80 × 0.333 + 30 = 26.6 + 30 = 56.6
 *   → 56.6 < 100, so request is ALLOWED
 *
 * This approximation assumes requests were evenly distributed across the
 * previous window — which is not always true, but good enough in practice.
 * Redis uses this approach for rate limiting at scale.
 *
 * Time complexity: O(1)
 * Space complexity: O(1) per key (2 counters + 1 timestamp)
 */

interface WindowCounterState {
  prevCount: number;    // count in the previous complete window
  currCount: number;    // count in the current (in-progress) window
  windowStart: number;  // epoch ms when the current window started
}

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

export class SlidingWindowCounterRateLimiter {
  private states: Map<string, WindowCounterState> = new Map();
  private mutexes: Map<string, Mutex> = new Map();

  constructor(
    private readonly limit: number,       // max requests per window
    private readonly windowMs: number     // window size in ms
  ) {}

  private getMutex(key: string): Mutex {
    if (!this.mutexes.has(key)) this.mutexes.set(key, new Mutex());
    return this.mutexes.get(key)!;
  }

  private getWindowStart(now: number): number {
    return now - (now % this.windowMs);
  }

  /**
   * CONCURRENCY NOTE: Same read-modify-write race as Fixed Window.
   * The mutex ensures no two concurrent requests can both pass the
   * estimate < limit check and both increment currCount unsafely.
   *
   * In distributed Redis implementations, you'd use:
   *   MULTI / EXEC (optimistic lock) or a Lua script for atomicity.
   */
  async allowRequest(key: string): Promise<{
    allowed: boolean;
    estimate: number;
    remaining: number;
  }> {
    const mutex = this.getMutex(key);
    await mutex.acquire();

    try {
      const now = Date.now();
      const currentWindowStart = this.getWindowStart(now);

      let state = this.states.get(key);

      if (!state) {
        state = { prevCount: 0, currCount: 0, windowStart: currentWindowStart };
        this.states.set(key, state);
      } else if (state.windowStart < currentWindowStart) {
        // We've moved into a new window — roll over
        const prevWindowStart = currentWindowStart - this.windowMs;

        if (state.windowStart === prevWindowStart) {
          // Just one window behind — roll current → previous
          state.prevCount = state.currCount;
        } else {
          // More than one window has passed with no requests — prev is 0
          state.prevCount = 0;
        }
        state.currCount = 0;
        state.windowStart = currentWindowStart;
      }

      // Fraction of current window that has elapsed (0.0 to 1.0)
      const elapsedFraction = (now - state.windowStart) / this.windowMs;

      // Weighted estimate: previous window contributes less as current window progresses
      const estimate = state.prevCount * (1 - elapsedFraction) + state.currCount;

      if (estimate >= this.limit) {
        return { allowed: false, estimate, remaining: 0 };
      }

      state.currCount++;
      const newEstimate = state.prevCount * (1 - elapsedFraction) + state.currCount;

      return {
        allowed: true,
        estimate: newEstimate,
        remaining: Math.max(0, Math.floor(this.limit - newEstimate)),
      };
    } finally {
      mutex.release();
    }
  }

  async getEstimate(key: string): Promise<{ estimate: number; elapsedFraction: number }> {
    const mutex = this.getMutex(key);
    await mutex.acquire();

    try {
      const now = Date.now();
      const currentWindowStart = this.getWindowStart(now);
      const state = this.states.get(key);

      if (!state || state.windowStart < currentWindowStart) {
        return { estimate: 0, elapsedFraction: (now - currentWindowStart) / this.windowMs };
      }

      const elapsedFraction = (now - state.windowStart) / this.windowMs;
      const estimate = state.prevCount * (1 - elapsedFraction) + state.currCount;

      return { estimate, elapsedFraction };
    } finally {
      mutex.release();
    }
  }
}

// ---------------------------------------------------------------------------
// Demo — shows weighted approximation and roll-over behavior
// ---------------------------------------------------------------------------
async function demo() {
  console.log("=== Sliding Window Counter Demo ===");
  console.log("Config: limit=10 requests per 1 second window\n");

  const limiter = new SlidingWindowCounterRateLimiter(10, 1000);

  // Fill up most of the first window
  console.log("--- Window 1: sending 8 requests ---");
  for (let i = 1; i <= 8; i++) {
    const res = await limiter.allowRequest("user:alice");
    console.log(`Req ${i}: ${res.allowed ? "ALLOWED" : "REJECTED"} | estimate=${res.estimate.toFixed(2)} | remaining≈${res.remaining}`);
  }

  // Wait 600ms — now 60% into the next window
  // Previous window (8 requests) contributes 8 × (1 - 0.6) = 3.2
  // So ~3.2 + 0 = 3.2 effective, ~6.8 slots remaining
  await new Promise((r) => setTimeout(r, 1100)); // let window roll over

  console.log("\n--- Window 2 (prev=8, elapsed≈60%): sending 5 requests ---");
  for (let i = 1; i <= 5; i++) {
    const res = await limiter.allowRequest("user:alice");
    const est = await limiter.getEstimate("user:alice");
    console.log(`Req ${i}: ${res.allowed ? "ALLOWED" : "REJECTED"} | estimate=${res.estimate.toFixed(2)} (elapsedFraction≈${est.elapsedFraction.toFixed(2)})`);
  }

  // Concurrent stress test
  console.log("\n--- 20 simultaneous requests (limit=5) ---");
  const limiter2 = new SlidingWindowCounterRateLimiter(5, 2000);
  const results = await Promise.all(
    Array.from({ length: 20 }, (_, i) =>
      limiter2.allowRequest("user:concurrent").then((r) => `R${i + 1}:${r.allowed ? "OK" : "NO"}`)
    )
  );
  const allowed = results.filter((r) => r.includes("OK")).length;
  console.log(results.join("  "));
  console.log(`Allowed: ${allowed}/20`);

  // Show approximation error comparison
  console.log("\n--- Approximation vs. exact count ---");
  console.log("Sliding Window Counter approximates the true count.");
  console.log("Error is at most (prev_count × window_fraction) which is bounded by the limit.");
  console.log("Worst case: prev window was full (10), current window at 50% → over-counts by up to 5.");
}

demo();
