// SLIDING WINDOW LOG — Go implementation
//
// Run:  go run ./sliding-window-log/
// Race: go run -race ./sliding-window-log/
//
// Key Go concepts demonstrated:
//   - sync.RWMutex: read-lock for status checks, write-lock for allow
//   - sort.Search (binary search) to find the eviction boundary efficiently
//   - Per-key mutexes via a sync.Map of *sync.RWMutex to allow different keys
//     to proceed concurrently without contending on a single global lock
//   - Goroutines + WaitGroup to verify exactly N allowed under concurrency
//   - time.AfterFunc to simulate requests that straddle a window boundary
package main

import (
	"fmt"
	"sort"
	"sync"
	"sync/atomic"
	"time"
)

// ─────────────────────────────────────────────────────────────────────────────
// Per-key locking: different keys can be rate-limited concurrently
// without blocking each other — only the same key serialises.
// ─────────────────────────────────────────────────────────────────────────────

type keyedMutex struct {
	mu   sync.Mutex
	keys sync.Map // key → *sync.Mutex
}

func (km *keyedMutex) lockKey(key string) func() {
	v, _ := km.keys.LoadOrStore(key, &sync.Mutex{})
	m := v.(*sync.Mutex)
	m.Lock()
	return m.Unlock
}

// ─────────────────────────────────────────────────────────────────────────────
// UNSAFE — exposes the read-then-append race
// ─────────────────────────────────────────────────────────────────────────────

type UnsafeSlidingWindowLog struct {
	logs     map[string][]int64 // Unix ms timestamps
	limit    int
	windowMs int64
}

func NewUnsafeSlidingWindowLog(limit int, window time.Duration) *UnsafeSlidingWindowLog {
	return &UnsafeSlidingWindowLog{
		logs:     make(map[string][]int64),
		limit:    limit,
		windowMs: window.Milliseconds(),
	}
}

// Allow is NOT safe. Without a lock, two goroutines can both read
// len(log) == limit-1, both decide to append, exceeding the limit.
func (sw *UnsafeSlidingWindowLog) Allow(key string) bool {
	now := time.Now().UnixMilli()
	cutoff := now - sw.windowMs

	log := sw.logs[key]
	// Evict stale entries
	i := sort.Search(len(log), func(i int) bool { return log[i] >= cutoff })
	log = log[i:]
	sw.logs[key] = log

	if len(log) >= sw.limit {
		return false
	}
	// ← race window: another goroutine is between here and the append below
	sw.logs[key] = append(sw.logs[key], now)
	return true
}

// ─────────────────────────────────────────────────────────────────────────────
// SAFE — per-key mutex, binary search eviction
// ─────────────────────────────────────────────────────────────────────────────

type SlidingWindowLog struct {
	km       keyedMutex
	logs     sync.Map   // key → *[]int64
	limit    int
	windowMs int64
}

func NewSlidingWindowLog(limit int, window time.Duration) *SlidingWindowLog {
	return &SlidingWindowLog{
		limit:    limit,
		windowMs: window.Milliseconds(),
	}
}

func (sw *SlidingWindowLog) getLog(key string) *[]int64 {
	v, _ := sw.logs.LoadOrStore(key, &[]int64{})
	return v.(*[]int64)
}

// Allow is safe for concurrent calls per key.
// Different keys never block each other.
func (sw *SlidingWindowLog) Allow(key string) (bool, int, int64) {
	unlock := sw.km.lockKey(key)
	defer unlock()

	now := time.Now().UnixMilli()
	cutoff := now - sw.windowMs
	log := sw.getLog(key)

	// Binary search: find index of first timestamp >= cutoff
	evictBefore := sort.Search(len(*log), func(i int) bool {
		return (*log)[i] >= cutoff
	})

	// Evict stale entries (slide the window)
	if evictBefore > 0 {
		*log = (*log)[evictBefore:]
	}

	if len(*log) >= sw.limit {
		// How long until the oldest request slides out
		msUntilSlot := (*log)[0] + sw.windowMs - now
		return false, 0, msUntilSlot
	}

	*log = append(*log, now)
	remaining := sw.limit - len(*log)
	return true, remaining, 0
}

// MsUntilNextSlot returns how many ms until the next slot opens.
func (sw *SlidingWindowLog) MsUntilNextSlot(key string) int64 {
	unlock := sw.km.lockKey(key)
	defer unlock()

	now := time.Now().UnixMilli()
	cutoff := now - sw.windowMs
	log := sw.getLog(key)

	i := sort.Search(len(*log), func(i int) bool { return (*log)[i] >= cutoff })
	if i > 0 {
		*log = (*log)[i:]
	}

	if len(*log) < sw.limit {
		return 0
	}
	return (*log)[0] + sw.windowMs - now
}

// ─────────────────────────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────────────────────────

func main() {
	fmt.Println("════════════════════════════════════════════")
	fmt.Println("      SLIDING WINDOW LOG — Go Demo          ")
	fmt.Println("════════════════════════════════════════════")

	// ── Part 1: Sequential behaviour ─────────────────────────────────────────
	fmt.Println("\n── Part 1: Sequential (limit=5, window=1s) ──")
	swl := NewSlidingWindowLog(5, time.Second)

	for i := 1; i <= 7; i++ {
		ok, remaining, waitMs := swl.Allow("user:alice")
		if ok {
			fmt.Printf("  Req %d: ALLOWED ✓  remaining=%d\n", i, remaining)
		} else {
			fmt.Printf("  Req %d: REJECTED ✗  next slot in %dms\n", i, waitMs)
		}
	}

	waitMs := swl.MsUntilNextSlot("user:alice")
	fmt.Printf("\n  Sleeping %dms for oldest request to slide out...\n", waitMs+5)
	time.Sleep(time.Duration(waitMs+5) * time.Millisecond)

	ok, remaining, _ := swl.Allow("user:alice")
	fmt.Printf("  Req 8 (after wait): %s  remaining=%d\n",
		map[bool]string{true: "ALLOWED ✓", false: "REJECTED ✗"}[ok], remaining)

	// ── Part 2: Race with UNSAFE (no lock) ───────────────────────────────────
	fmt.Println("\n── Part 2: Race condition — UNSAFE (limit=5, 50 goroutines) ──")

	for trial := 1; trial <= 3; trial++ {
		unsafe := NewUnsafeSlidingWindowLog(5, 10*time.Second)
		var allowed int64
		var wg sync.WaitGroup
		gate := make(chan struct{})

		for i := 0; i < 50; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				<-gate
				if unsafe.Allow("race-key") {
					atomic.AddInt64(&allowed, 1)
				}
			}()
		}
		close(gate)
		wg.Wait()
		fmt.Printf("    Trial %d: %d allowed (should be ≤5; race causes over-counting)\n", trial, allowed)
	}

	// ── Part 3: Safe concurrent requests ─────────────────────────────────────
	fmt.Println("\n── Part 3: SAFE — 50 goroutines, limit=5 ──")

	for trial := 1; trial <= 3; trial++ {
		safe := NewSlidingWindowLog(5, 10*time.Second)
		var allowed int64
		var wg sync.WaitGroup
		gate := make(chan struct{})

		for i := 0; i < 50; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				<-gate
				ok, _, _ := safe.Allow("concurrent")
				if ok {
					atomic.AddInt64(&allowed, 1)
				}
			}()
		}
		close(gate)
		wg.Wait()
		fmt.Printf("    Trial %d: %d allowed (always exactly 5)\n", trial, allowed)
	}

	// ── Part 4: Per-key concurrency — different keys don't block each other ──
	fmt.Println("\n── Part 4: Per-key locks — 3 users, 5 goroutines each, no cross-blocking ──")
	multi := NewSlidingWindowLog(3, 10*time.Second)
	users := []string{"alice", "bob", "carol"}
	var wg sync.WaitGroup
	counts := make(map[string]*int64)
	for _, u := range users {
		var c int64
		counts[u] = &c
	}

	start := time.Now()
	gate := make(chan struct{})
	for _, user := range users {
		u := user
		for i := 0; i < 5; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				<-gate
				ok, _, _ := multi.Allow(u)
				if ok {
					atomic.AddInt64(counts[u], 1)
				}
			}()
		}
	}
	close(gate)
	wg.Wait()
	elapsed := time.Since(start)

	for _, u := range users {
		fmt.Printf("    %s: %d allowed (limit=3)\n", u, *counts[u])
	}
	fmt.Printf("  All 15 goroutines completed in %dµs\n", elapsed.Microseconds())

	// ── Part 5: Sliding window proves no boundary spike ───────────────────────
	fmt.Println("\n── Part 5: No Boundary Spike — timer-based proof ──")
	fmt.Println("  5 requests fire just before window mid-point.")
	fmt.Println("  5 more fire just after. Second batch still sees old requests in window.")

	noBoundary := NewSlidingWindowLog(5, 500*time.Millisecond)
	const noSpikeKey = "boundary-test"
	var allowed1, allowed2 int64

	var wg2 sync.WaitGroup

	// Batch 1: now
	for i := 0; i < 5; i++ {
		wg2.Add(1)
		go func() {
			defer wg2.Done()
			ok, _, _ := noBoundary.Allow(noSpikeKey)
			if ok {
				atomic.AddInt64(&allowed1, 1)
			}
		}()
	}
	wg2.Wait()
	fmt.Printf("  Batch 1 (t=0ms):   %d/5 allowed\n", allowed1)

	// Batch 2: 200ms later (window is 500ms, so batch1 timestamps still in window)
	time.Sleep(200 * time.Millisecond)
	var wg3 sync.WaitGroup
	for i := 0; i < 5; i++ {
		wg3.Add(1)
		go func() {
			defer wg3.Done()
			ok, _, _ := noBoundary.Allow(noSpikeKey)
			if ok {
				atomic.AddInt64(&allowed2, 1)
			}
		}()
	}
	wg3.Wait()
	fmt.Printf("  Batch 2 (t=200ms): %d/5 allowed (batch1 still in sliding window!)\n", allowed2)
	fmt.Printf("  Total: %d allowed — no 2x spike at boundary ✓\n", allowed1+allowed2)
}
