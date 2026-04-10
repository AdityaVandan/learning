/**
 * FIXED WINDOW COUNTER ALGORITHM
 *
 * Concept: Time is divided into fixed-size windows (e.g., each minute).
 * A counter tracks requests per window per key. When the counter exceeds
 * the limit, requests are rejected until the window resets.
 *
 * Simple to implement but suffers from the "boundary spike" problem:
 * A client can make 2× the allowed requests by clustering at the end of
 * one window and the start of the next.
 *
 *   Window 1       Window 2
 *   |.....|XXXXX| |XXXXX.....|
 *              ^boundary
 *   10 requests in last 10s of window1 + 10 in first 10s of window2
 *   = 20 requests in a 20s span despite a "10/min" limit.
 *
 * Time complexity: O(1)
 * Space complexity: O(1) per key (just a counter + window timestamp)
 */

interface WindowState {
  count: number;
  windowStart: number; // epoch ms of the current window's start
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

export class FixedWindowRateLimiter {
  private windows: Map<string, WindowState> = new Map();
  private mutexes: Map<string, Mutex> = new Map();

  constructor(
    private readonly limit: number,        // max requests per window
    private readonly windowSizeMs: number  // window duration in ms
  ) {}

  private getMutex(key: string): Mutex {
    if (!this.mutexes.has(key)) this.mutexes.set(key, new Mutex());
    return this.mutexes.get(key)!;
  }

  /**
   * CONCURRENCY NOTE: The mutex is critical here. Without it:
   *   Thread A reads count=9 (limit=10) → passes check
   *   Thread B reads count=9 (limit=10) → passes check
   *   Both increment → count becomes 11 (over limit!)
   *
   * With the mutex, one thread increments first, then the other
   * reads the updated count=10 and is correctly rejected.
   */
  async allowRequest(key: string): Promise<{ allowed: boolean; remaining: number; resetInMs: number }> {
    const mutex = this.getMutex(key);
    await mutex.acquire();

    try {
      const now = Date.now();
      const windowStart = now - (now % this.windowSizeMs); // align to window boundary

      let state = this.windows.get(key);

      // If no state or we've crossed into a new window, reset
      if (!state || state.windowStart < windowStart) {
        state = { count: 0, windowStart };
        this.windows.set(key, state);
      }

      const resetInMs = (state.windowStart + this.windowSizeMs) - now;

      if (state.count >= this.limit) {
        return { allowed: false, remaining: 0, resetInMs };
      }

      state.count++;
      return {
        allowed: true,
        remaining: this.limit - state.count,
        resetInMs,
      };
    } finally {
      mutex.release();
    }
  }

  async getStatus(key: string): Promise<{ count: number; remaining: number; resetInMs: number }> {
    const mutex = this.getMutex(key);
    await mutex.acquire();

    try {
      const now = Date.now();
      const windowStart = now - (now % this.windowSizeMs);
      const state = this.windows.get(key);

      if (!state || state.windowStart < windowStart) {
        return { count: 0, remaining: this.limit, resetInMs: this.windowSizeMs };
      }

      return {
        count: state.count,
        remaining: this.limit - state.count,
        resetInMs: (state.windowStart + this.windowSizeMs) - now,
      };
    } finally {
      mutex.release();
    }
  }
}

/**
 * Demonstrates the boundary spike problem with Fixed Window.
 * At t=950ms (near end of window), 5 requests pass.
 * At t=1050ms (start of next window), 5 more requests pass.
 * In the 100ms span across the boundary: 10 requests allowed despite limit=5/window.
 */
async function demonstrateBoundarySpike() {
  console.log("\n--- Boundary Spike Problem ---");

  // Use a tiny 1-second window to make the demo fast
  const limiter = new FixedWindowRateLimiter(5, 1000);

  // Simulate time near end of window (950ms into window)
  // We'll just send requests quickly then wait and send more
  console.log("Sending 5 requests near end of window 1:");
  for (let i = 1; i <= 5; i++) {
    const res = await limiter.allowRequest("spike-demo");
    console.log(`  Req ${i}: ${res.allowed ? "ALLOWED" : "REJECTED"} (remaining=${res.remaining})`);
  }

  // This 6th request should be rejected
  const res6 = await limiter.allowRequest("spike-demo");
  console.log(`  Req 6 (over limit): ${res6.allowed ? "ALLOWED" : "REJECTED"}`);

  // Wait for next window
  await new Promise((r) => setTimeout(r, 1100));

  console.log("\nSending 5 requests at start of window 2:");
  for (let i = 7; i <= 11; i++) {
    const res = await limiter.allowRequest("spike-demo");
    console.log(`  Req ${i}: ${res.allowed ? "ALLOWED" : "REJECTED"} (remaining=${res.remaining})`);
  }

  console.log("\n=> Near a boundary: 10 requests passed in a short span (5+5)");
  console.log("=> This is the fixed-window boundary spike vulnerability");
}

// ---------------------------------------------------------------------------
// Demo
// ---------------------------------------------------------------------------
async function demo() {
  console.log("=== Fixed Window Counter Demo ===");
  console.log("Config: limit=5 requests, window=1 second\n");

  const limiter = new FixedWindowRateLimiter(5, 1000);

  // 7 rapid requests — only first 5 pass
  for (let i = 1; i <= 7; i++) {
    const res = await limiter.allowRequest("user:alice");
    console.log(`Request ${i}: ${res.allowed ? "ALLOWED" : "REJECTED"} | remaining=${res.remaining} | resetIn=${res.resetInMs}ms`);
  }

  // Concurrent requests
  console.log("\n--- 10 simultaneous requests (limit=3) ---");
  const limiter2 = new FixedWindowRateLimiter(3, 5000);
  const results = await Promise.all(
    Array.from({ length: 10 }, (_, i) =>
      limiter2.allowRequest("user:bob").then((r) => `R${i + 1}:${r.allowed ? "OK" : "NO"}`)
    )
  );
  console.log(results.join("  "));

  await demonstrateBoundarySpike();
}

demo();
