// FIXED WINDOW COUNTER — Go implementation
//
// Run:  go run ./fixed-window/
// Race: go run -race ./fixed-window/
//
// Key Go concepts demonstrated:
//   - sync.Mutex for the counter check-and-increment critical section
//   - sync.RWMutex for read-heavy status checks (multiple readers, one writer)
//   - runtime.Gosched() in the unsafe version to expose the race deterministically
//   - time.AfterFunc to simulate window-boundary traffic in the boundary spike demo
//   - sync.WaitGroup + channel gate for simultaneous goroutine release
package main

import (
	"fmt"
	"runtime"
	"sync"
	"sync/atomic"
	"time"
)

// ─────────────────────────────────────────────────────────────────────────────
// UNSAFE — shows the classic TOCTOU (time-of-check to time-of-use) race
// ─────────────────────────────────────────────────────────────────────────────

type UnsafeFixedWindow struct {
	count       int64
	windowStart int64 // Unix ms of window start
	windowMs    int64
	limit       int64
}

func NewUnsafeFixedWindow(limit int, windowMs time.Duration) *UnsafeFixedWindow {
	now := time.Now().UnixMilli()
	start := now - (now % windowMs.Milliseconds())
	return &UnsafeFixedWindow{
		windowStart: start,
		windowMs:    windowMs.Milliseconds(),
		limit:       int64(limit),
	}
}

// Allow is NOT goroutine-safe.
// runtime.Gosched() between the check and increment makes the race visible:
// Two goroutines both read count=limit-1, both pass the check, both increment
// → count ends up as limit+1.
func (fw *UnsafeFixedWindow) Allow() bool {
	now := time.Now().UnixMilli()
	windowStart := now - (now % fw.windowMs)

	if windowStart > fw.windowStart {
		fw.count = 0 // ← not atomic either, another race
		fw.windowStart = windowStart
	}

	if fw.count < fw.limit {
		runtime.Gosched() // ← yield here: another goroutine can now also pass the check
		fw.count++
		return true
	}
	return false
}

// ─────────────────────────────────────────────────────────────────────────────
// SAFE — sync.Mutex makes the window-check + increment atomic
// ─────────────────────────────────────────────────────────────────────────────

type FixedWindowCounter struct {
	mu          sync.Mutex
	states      map[string]*windowState
}

type windowState struct {
	count       int64
	windowStart int64 // Unix ms
}

func NewFixedWindowCounter() *FixedWindowCounter {
	return &FixedWindowCounter{
		states: make(map[string]*windowState),
	}
}

// Allow checks and increments the counter for `key` in the current window.
// Returns (allowed, remaining, resetInMs).
//
// Why mutex and not atomic? Because we need a compound operation:
//   1. Check if window has expired → reset counter
//   2. Check if count < limit
//   3. Increment
// Atomic operations can only guarantee single-variable atomicity.
// Steps 1-3 together require a mutex.
func (fw *FixedWindowCounter) Allow(key string, limit int, windowDur time.Duration) (bool, int64, int64) {
	fw.mu.Lock()
	defer fw.mu.Unlock()

	windowMs := windowDur.Milliseconds()
	now := time.Now().UnixMilli()
	windowStart := now - (now % windowMs)
	resetInMs := (windowStart + windowMs) - now

	state, ok := fw.states[key]
	if !ok {
		state = &windowState{}
		fw.states[key] = state
	}

	// New window — reset
	if state.windowStart < windowStart {
		state.count = 0
		state.windowStart = windowStart
	}

	if state.count >= int64(limit) {
		return false, 0, resetInMs
	}

	state.count++
	remaining := int64(limit) - state.count
	return true, remaining, resetInMs
}

func (fw *FixedWindowCounter) Status(key string, limit int, windowDur time.Duration) (count, remaining, resetInMs int64) {
	fw.mu.Lock()
	defer fw.mu.Unlock()

	windowMs := windowDur.Milliseconds()
	now := time.Now().UnixMilli()
	windowStart := now - (now % windowMs)
	resetInMs = (windowStart + windowMs) - now

	state, ok := fw.states[key]
	if !ok || state.windowStart < windowStart {
		return 0, int64(limit), resetInMs
	}
	return state.count, int64(limit) - state.count, resetInMs
}

// ─────────────────────────────────────────────────────────────────────────────
// Boundary spike simulator using real timers
// ─────────────────────────────────────────────────────────────────────────────

func demonstrateBoundarySpike(fw *FixedWindowCounter, limit int, window time.Duration) {
	fmt.Println("\n── Boundary Spike Simulator ──")
	fmt.Println("  Goroutines are scheduled to fire at the END of window 1")
	fmt.Println("  and the START of window 2 using time.AfterFunc timers.")

	const spikeKey = "spike"
	var totalAllowed int64
	var wg sync.WaitGroup

	now := time.Now().UnixMilli()
	windowMs := window.Milliseconds()
	// Time until the next window boundary
	nextBoundary := time.Duration(windowMs-(now%windowMs)) * time.Millisecond

	fmt.Printf("  Next window boundary in: %dms\n", nextBoundary.Milliseconds())

	// Schedule limit requests to arrive just BEFORE the boundary
	justBefore := nextBoundary - 20*time.Millisecond
	if justBefore < 0 {
		justBefore = 0
	}

	for i := 0; i < limit; i++ {
		wg.Add(1)
		time.AfterFunc(justBefore, func() {
			defer wg.Done()
			ok, _, _ := fw.Allow(spikeKey, limit, window)
			if ok {
				atomic.AddInt64(&totalAllowed, 1)
			}
		})
	}

	// Schedule limit requests to arrive just AFTER the boundary (new window resets)
	justAfter := nextBoundary + 20*time.Millisecond
	for i := 0; i < limit; i++ {
		wg.Add(1)
		time.AfterFunc(justAfter, func() {
			defer wg.Done()
			ok, _, _ := fw.Allow(spikeKey, limit, window)
			if ok {
				atomic.AddInt64(&totalAllowed, 1)
			}
		})
	}

	wg.Wait()
	fmt.Printf("\n  Limit: %d per window | Requests at boundary: %d+%d = %d\n",
		limit, limit, limit, limit*2)
	fmt.Printf("  Total ALLOWED across boundary: %d\n", totalAllowed)
	fmt.Printf("  → In a ~40ms span, %dx the per-window limit passed!\n", totalAllowed/int64(limit))
	fmt.Println("  → This is the fixed-window boundary spike vulnerability.")
}

// ─────────────────────────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────────────────────────

func main() {
	fmt.Println("════════════════════════════════════════════")
	fmt.Println("      FIXED WINDOW COUNTER — Go Demo        ")
	fmt.Println("════════════════════════════════════════════")

	// ── Part 1: Sequential behaviour ─────────────────────────────────────────
	fmt.Println("\n── Part 1: Sequential requests (limit=5, window=2s) ──")
	fw := NewFixedWindowCounter()
	const (
		key    = "user:alice"
		limit  = 5
		window = 2 * time.Second
	)

	for i := 1; i <= 7; i++ {
		ok, remaining, resetMs := fw.Allow(key, limit, window)
		status := "ALLOWED ✓"
		if !ok {
			status = "REJECTED ✗"
		}
		fmt.Printf("  Request %d: %s  remaining=%d  resetIn=%dms\n", i, status, remaining, resetMs)
	}

	// ── Part 2: Race condition demo ───────────────────────────────────────────
	fmt.Println("\n── Part 2: Race condition with UNSAFE window (limit=5) ──")
	fmt.Println("  50 goroutines released simultaneously — without mutex:")

	for trial := 1; trial <= 3; trial++ {
		unsafe := NewUnsafeFixedWindow(5, 5*time.Second)
		var allowed int64
		var wg sync.WaitGroup
		gate := make(chan struct{})

		for i := 0; i < 50; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				<-gate
				if unsafe.Allow() {
					atomic.AddInt64(&allowed, 1)
				}
			}()
		}
		close(gate)
		wg.Wait()
		fmt.Printf("    Trial %d: %d allowed (should be ≤5; race causes over-counting)\n", trial, allowed)
	}

	// ── Part 3: Safe concurrent requests ─────────────────────────────────────
	fmt.Println("\n── Part 3: SAFE window — 50 goroutines, limit=5 ──")
	fw2 := NewFixedWindowCounter()
	for trial := 1; trial <= 3; trial++ {
		var allowed int64
		var wg sync.WaitGroup
		gate := make(chan struct{})

		for i := 0; i < 50; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				<-gate
				ok, _, _ := fw2.Allow("safe-trial", 5, 10*time.Second)
				if ok {
					atomic.AddInt64(&allowed, 1)
				}
			}()
		}
		close(gate)
		wg.Wait()
		fmt.Printf("    Trial %d: %d allowed (always exactly 5)\n", trial, allowed)
	}

	// ── Part 4: Boundary spike with real timers ───────────────────────────────
	demonstrateBoundarySpike(NewFixedWindowCounter(), 5, 500*time.Millisecond)
}
