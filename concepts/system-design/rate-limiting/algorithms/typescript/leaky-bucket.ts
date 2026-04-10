/**
 * LEAKY BUCKET ALGORITHM
 *
 * Concept: Requests enter a fixed-size queue (the "bucket"). A processor
 * drains the queue at a constant rate, forwarding one request per interval.
 * If the queue is full, new requests overflow and are rejected.
 *
 * Unlike Token Bucket, Leaky Bucket produces a perfectly smooth output rate —
 * it cannot burst. It is useful when downstream services need steady traffic.
 *
 * Two implementation modes:
 *   1. As a queue (classical) — requests wait in queue, processed at fixed rate
 *   2. As a counter (simplified) — just tracks fill level without actual queuing
 *
 * Time complexity: O(1) enqueue/dequeue
 * Space complexity: O(capacity) per key (the queue)
 */

interface QueuedRequest {
  resolve: (allowed: boolean) => void;
  enqueuedAt: number;
}

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
    if (next) next();
    else this.locked = false;
  }
}

/**
 * Classical Leaky Bucket — requests are enqueued and dripped out at a
 * steady rate. Requests that arrive when the queue is full are rejected
 * immediately. Queued requests are resolved after their turn.
 */
export class LeakyBucketRateLimiter {
  // Per-key queue of waiting requests
  private queues: Map<string, QueuedRequest[]> = new Map();
  private mutexes: Map<string, Mutex> = new Map();
  // Timer handles for each key's drip processor
  private drippers: Map<string, ReturnType<typeof setInterval>> = new Map();

  constructor(
    private readonly capacity: number,   // max queue depth
    private readonly leakRateMs: number, // ms between each drip (processed request)
  ) {}

  private getMutex(key: string): Mutex {
    if (!this.mutexes.has(key)) this.mutexes.set(key, new Mutex());
    return this.mutexes.get(key)!;
  }

  private ensureDripper(key: string): void {
    if (this.drippers.has(key)) return;

    const interval = setInterval(async () => {
      const mutex = this.getMutex(key);
      await mutex.acquire();

      try {
        const q = this.queues.get(key);
        if (!q || q.length === 0) {
          // Queue empty — stop the drip timer to avoid resource leak
          clearInterval(this.drippers.get(key)!);
          this.drippers.delete(key);
          return;
        }
        // Drip: process the oldest request in the queue (FIFO)
        const next = q.shift()!;
        next.resolve(true); // signal to the caller: request is now processed
      } finally {
        mutex.release();
      }
    }, this.leakRateMs);

    this.drippers.set(key, interval);
  }

  /**
   * Attempt to enqueue the request. Returns a Promise that resolves to:
   *   true  — the request was eventually processed (leaked out)
   *   false — bucket was full, request rejected immediately
   *
   * CONCURRENCY NOTE: The mutex guards the check-then-enqueue step so two
   * concurrent requests cannot both see a queue at capacity-1 and both
   * successfully enqueue (which would overflow the bucket).
   */
  async allowRequest(key: string): Promise<boolean> {
    const mutex = this.getMutex(key);
    await mutex.acquire();

    try {
      if (!this.queues.has(key)) this.queues.set(key, []);
      const q = this.queues.get(key)!;

      if (q.length >= this.capacity) {
        return false; // bucket is full — overflow / reject
      }

      return new Promise<boolean>((resolve) => {
        q.push({ resolve, enqueuedAt: Date.now() });
        this.ensureDripper(key); // start dripping if not already running
      });
    } finally {
      mutex.release();
    }
  }

  getQueueDepth(key: string): number {
    return this.queues.get(key)?.length ?? 0;
  }

  /** Clean up timers — call this when shutting down */
  destroy(): void {
    for (const timer of this.drippers.values()) {
      clearInterval(timer);
    }
    this.drippers.clear();
  }
}

/**
 * Counter-based Leaky Bucket — a simpler variant that does NOT queue
 * requests. It only tracks the conceptual "water level" and rejects
 * requests when the bucket is full. Leaks happen continuously over time.
 *
 * This is faster and stateless (no actual queue) but doesn't smooth output
 * the way the classical variant does.
 */
export class LeakyBucketCounter {
  private levels: Map<string, { level: number; lastLeakTime: number }> = new Map();
  private mutexes: Map<string, Mutex> = new Map();

  constructor(
    private readonly capacity: number,     // max level
    private readonly leakRatePerSec: number // units leaked per second
  ) {}

  private getMutex(key: string): Mutex {
    if (!this.mutexes.has(key)) this.mutexes.set(key, new Mutex());
    return this.mutexes.get(key)!;
  }

  async allowRequest(key: string): Promise<boolean> {
    const mutex = this.getMutex(key);
    await mutex.acquire();

    try {
      const now = Date.now();
      if (!this.levels.has(key)) {
        this.levels.set(key, { level: 0, lastLeakTime: now });
      }

      const state = this.levels.get(key)!;
      const elapsedSec = (now - state.lastLeakTime) / 1000;
      const leaked = elapsedSec * this.leakRatePerSec;

      // Water drains out — level never goes below 0
      state.level = Math.max(0, state.level - leaked);
      state.lastLeakTime = now;

      if (state.level + 1 > this.capacity) {
        return false; // bucket would overflow
      }

      state.level += 1; // add one unit of water for this request
      return true;
    } finally {
      mutex.release();
    }
  }
}

// ---------------------------------------------------------------------------
// Demo
// ---------------------------------------------------------------------------
async function demo() {
  console.log("=== Leaky Bucket (Classical Queue) Demo ===");
  console.log("Config: capacity=3 queue slots, leak every 200ms\n");

  const limiter = new LeakyBucketRateLimiter(3, 200);

  // Fire 5 simultaneous requests; only 3 fit in the queue
  const requests = Array.from({ length: 5 }, (_, i) =>
    limiter.allowRequest("user:alice").then((ok) => {
      console.log(`Request ${i + 1}: ${ok ? "PROCESSED" : "REJECTED (bucket full)"}`);
    })
  );
  await Promise.all(requests);

  limiter.destroy();

  console.log("\n=== Leaky Bucket (Counter) Demo ===");
  console.log("Config: capacity=4, leakRate=2/sec\n");

  const counter = new LeakyBucketCounter(4, 2);

  for (let i = 1; i <= 6; i++) {
    const ok = await counter.allowRequest("user:bob");
    console.log(`Request ${i}: ${ok ? "ALLOWED" : "REJECTED"}`);
  }

  await new Promise((r) => setTimeout(r, 1000)); // 2 units drain in 1 sec
  console.log("\nAfter 1s (2 units drained):");
  for (let i = 7; i <= 9; i++) {
    const ok = await counter.allowRequest("user:bob");
    console.log(`Request ${i}: ${ok ? "ALLOWED" : "REJECTED"}`);
  }
}

demo();
