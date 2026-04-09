// TOKEN BUCKET — Go implementation
//
// Run:  go run ./token-bucket/
// Race: go run -race ./token-bucket/
//
// Key Go concepts demonstrated:
//   - sync.Mutex to serialise the refill → check → deduct sequence
//   - Goroutines + sync.WaitGroup to fire truly parallel requests
//   - runtime.Gosched() in the unsafe version to force the scheduler
//     to switch goroutines at the exact vulnerable moment, making the
//     race condition reliably reproducible
package main

import (
	"fmt"
	"runtime"
	"sync"
	"sync/atomic"
	"time"
)

// ─────────────────────────────────────────────────────────────────────────────
// UNSAFE implementation — NO mutex, race condition is intentionally exposed
// ─────────────────────────────────────────────────────────────────────────────

type UnsafeTokenBucket struct {
	tokens     float64
	capacity   float64
	refillRate float64 // tokens per second
	lastRefill time.Time
}

func NewUnsafeTokenBucket(capacity, refillRate float64) *UnsafeTokenBucket {
	return &UnsafeTokenBucket{
		tokens:     capacity,
		capacity:   capacity,
		refillRate: refillRate,
		lastRefill: time.Now(),
	}
}

// Allow is NOT safe for concurrent use — no mutex protects the read-modify-write.
// runtime.Gosched() is inserted at the critical gap to force the Go scheduler
// to context-switch to another goroutine between the CHECK and the DEDUCT,
// making the race reliably visible (not just theoretically possible).
func (tb *UnsafeTokenBucket) Allow() bool {
	now := time.Now()
	elapsed := now.Sub(tb.lastRefill).Seconds()
	if tb.tokens+elapsed*tb.refillRate < tb.capacity {
		tb.tokens += elapsed * tb.refillRate
	} else {
		tb.tokens = tb.capacity
	}
	tb.lastRefill = now

	// ← CHECK: goroutine reads "tokens >= 1" — both goroutines can be here
	if tb.tokens >= 1 {
		runtime.Gosched() // ← force scheduler switch NOW, before deducting
		// ← Another goroutine runs, also sees tokens >= 1, also decides to allow
		tb.tokens-- // ← both goroutines decrement; one pushes tokens negative
		return true
	}
	return false
}

// ─────────────────────────────────────────────────────────────────────────────
// SAFE implementation — sync.Mutex makes refill+check+deduct atomic
// ─────────────────────────────────────────────────────────────────────────────

type TokenBucket struct {
	mu         sync.Mutex
	tokens     float64
	capacity   float64
	refillRate float64
	lastRefill time.Time
}

func NewTokenBucket(capacity, refillRate float64) *TokenBucket {
	return &TokenBucket{
		tokens:     capacity,
		capacity:   capacity,
		refillRate: refillRate,
		lastRefill: time.Now(),
	}
}

func (tb *TokenBucket) refill() {
	// Called inside the lock — safe to read/write fields
	now := time.Now()
	elapsed := now.Sub(tb.lastRefill).Seconds()
	tb.tokens = min(tb.capacity, tb.tokens+elapsed*tb.refillRate)
	tb.lastRefill = now
}

// Allow is safe for concurrent use from any number of goroutines.
// The mutex ensures that between refill and deduct, no other goroutine
// can observe or modify the token count.
func (tb *TokenBucket) Allow() bool {
	tb.mu.Lock()
	defer tb.mu.Unlock()

	tb.refill()

	if tb.tokens >= 1 {
		tb.tokens--
		return true
	}
	return false
}

func (tb *TokenBucket) Tokens() float64 {
	tb.mu.Lock()
	defer tb.mu.Unlock()
	tb.refill()
	return tb.tokens
}

// ─────────────────────────────────────────────────────────────────────────────
// Demo helpers
// ─────────────────────────────────────────────────────────────────────────────

func min(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

// fireNConcurrent sends n goroutines at the same instant (all blocked on a
// shared channel, then released together) to maximise scheduling contention.
func fireNConcurrent(n int, allowFn func() bool) (allowed, rejected int) {
	var (
		wg          sync.WaitGroup
		allowedCount int64
		rejectedCount int64
		start       = make(chan struct{}) // all goroutines wait here
	)

	for i := 0; i < n; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			<-start // block until all goroutines are spawned
			if allowFn() {
				atomic.AddInt64(&allowedCount, 1)
			} else {
				atomic.AddInt64(&rejectedCount, 1)
			}
		}()
	}

	close(start) // release all goroutines simultaneously
	wg.Wait()
	return int(allowedCount), int(rejectedCount)
}

// ─────────────────────────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────────────────────────

func main() {
	fmt.Println("════════════════════════════════════════════")
	fmt.Println("         TOKEN BUCKET — Go Demo             ")
	fmt.Println("════════════════════════════════════════════")

	// ── Part 1: Sequential behaviour ─────────────────────────────────────────
	fmt.Println("\n── Part 1: Sequential requests (capacity=5, refill=2/sec) ──")
	tb := NewTokenBucket(5, 2)

	for i := 1; i <= 7; i++ {
		ok := tb.Allow()
		status := "ALLOWED ✓"
		if !ok {
			status = "REJECTED ✗"
		}
		fmt.Printf("  Request %d: %s  (tokens remaining: %.1f)\n", i, status, tb.Tokens())
	}

	fmt.Println("\n  Waiting 1s for refill (2 new tokens)...")
	time.Sleep(time.Second)

	for i := 8; i <= 10; i++ {
		ok := tb.Allow()
		status := "ALLOWED ✓"
		if !ok {
			status = "REJECTED ✗"
		}
		fmt.Printf("  Request %d: %s  (tokens remaining: %.1f)\n", i, status, tb.Tokens())
	}

	// ── Part 2: Race condition demo (UNSAFE) ──────────────────────────────────
	fmt.Println("\n── Part 2: Race condition with UNSAFE bucket (capacity=3) ──")
	fmt.Println("  Expected: exactly 3 ALLOWED (capacity=3), rest REJECTED")
	fmt.Println("  Reality with no mutex:")

	for trial := 1; trial <= 3; trial++ {
		unsafe := NewUnsafeTokenBucket(3, 0) // refillRate=0: no refill during test
		allowed, rejected := fireNConcurrent(10, unsafe.Allow)
		fmt.Printf("  Trial %d: allowed=%d rejected=%d  (tokens drifted to: %.1f)\n",
			trial, allowed, rejected, unsafe.tokens)
	}
	fmt.Println("  ^ Allowed count varies across trials — non-deterministic race!")

	// ── Part 3: Safe concurrent requests ─────────────────────────────────────
	fmt.Println("\n── Part 3: SAFE bucket under 50 simultaneous goroutines (capacity=10) ──")
	safe := NewTokenBucket(10, 0)
	allowed, rejected := fireNConcurrent(50, safe.Allow)
	fmt.Printf("  Allowed: %d  Rejected: %d  (always exactly 10 allowed)\n", allowed, rejected)

	// ── Part 4: Refill over time with concurrent senders ─────────────────────
	fmt.Println("\n── Part 4: Refill over time with background senders ──")
	fmt.Println("  1 sender goroutine per 100ms, bucket capacity=5, refill=10/sec")

	tb2 := NewTokenBucket(5, 10)
	var sent, passed, blocked int64
	var wg sync.WaitGroup

	// Send a request every 100ms for 1 second (10 total)
	ticker := time.NewTicker(100 * time.Millisecond)
	done := time.After(1 * time.Second)

loop:
	for {
		select {
		case <-ticker.C:
			wg.Add(1)
			go func() {
				defer wg.Done()
				atomic.AddInt64(&sent, 1)
				if tb2.Allow() {
					atomic.AddInt64(&passed, 1)
				} else {
					atomic.AddInt64(&blocked, 1)
				}
			}()
		case <-done:
			break loop
		}
	}
	ticker.Stop()
	wg.Wait()
	fmt.Printf("  Sent: %d  Passed: %d  Blocked: %d\n", sent, passed, blocked)
}
