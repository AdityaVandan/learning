// SLIDING WINDOW COUNTER (HYBRID) — Go implementation
//
// Run:  go run ./sliding-window-counter/
// Race: go run -race ./sliding-window-counter/
//
// Key Go concepts demonstrated:
//   - sync.Mutex for the atomic estimate → check → increment sequence
//   - time.Ticker to simulate a background "request generator" goroutine
//     that gradually fills windows and triggers a rollover
//   - sync.WaitGroup + channel gate for simultaneous goroutine release
//   - Comparing approximation vs exact count to show error bounds
//   - sync.Map for concurrent per-key state without a global lock
package main

import (
	"fmt"
	"math"
	"sync"
	"sync/atomic"
	"time"
)

// ─────────────────────────────────────────────────────────────────────────────
// UNSAFE — demonstrates the read-modify-write race
// ─────────────────────────────────────────────────────────────────────────────

type unsafeState struct {
	prevCount    float64
	currCount    float64
	windowStart  int64 // Unix ms
}

type UnsafeSlidingWindowCounter struct {
	states   map[string]*unsafeState
	limit    float64
	windowMs int64
}

func NewUnsafeSlidingWindowCounter(limit int, window time.Duration) *UnsafeSlidingWindowCounter {
	return &UnsafeSlidingWindowCounter{
		states:   make(map[string]*unsafeState),
		limit:    float64(limit),
		windowMs: window.Milliseconds(),
	}
}

func (sw *UnsafeSlidingWindowCounter) Allow(key string) bool {
	now := time.Now().UnixMilli()
	windowStart := now - (now % sw.windowMs)

	s, ok := sw.states[key]
	if !ok {
		s = &unsafeState{windowStart: windowStart}
		sw.states[key] = s
	}

	if s.windowStart < windowStart {
		prevWS := windowStart - sw.windowMs
		if s.windowStart == prevWS {
			s.prevCount = s.currCount
		} else {
			s.prevCount = 0
		}
		s.currCount = 0
		s.windowStart = windowStart
	}

	elapsed := float64(now-s.windowStart) / float64(sw.windowMs)
	estimate := s.prevCount*(1-elapsed) + s.currCount

	if estimate >= sw.limit {
		return false
	}
	// ← race: another goroutine between check and increment sees same estimate
	s.currCount++
	return true
}

// ─────────────────────────────────────────────────────────────────────────────
// SAFE — per-key mutex via sync.Map
// ─────────────────────────────────────────────────────────────────────────────

type swcState struct {
	mu          sync.Mutex
	prevCount   float64
	currCount   float64
	windowStart int64
}

type SlidingWindowCounter struct {
	states   sync.Map // key → *swcState
	limit    float64
	windowMs int64
}

func NewSlidingWindowCounter(limit int, window time.Duration) *SlidingWindowCounter {
	return &SlidingWindowCounter{
		limit:    float64(limit),
		windowMs: window.Milliseconds(),
	}
}

func (sw *SlidingWindowCounter) getState(key string) *swcState {
	v, _ := sw.states.LoadOrStore(key, &swcState{})
	return v.(*swcState)
}

// Allow is safe for concurrent use per key.
// Returns (allowed, estimate, remaining).
func (sw *SlidingWindowCounter) Allow(key string) (bool, float64, int) {
	s := sw.getState(key)
	s.mu.Lock()
	defer s.mu.Unlock()

	now := time.Now().UnixMilli()
	windowStart := now - (now % sw.windowMs)

	if s.windowStart < windowStart {
		prevWS := windowStart - sw.windowMs
		if s.windowStart == prevWS {
			s.prevCount = s.currCount
		} else {
			s.prevCount = 0
		}
		s.currCount = 0
		s.windowStart = windowStart
	}

	elapsedFraction := float64(now-s.windowStart) / float64(sw.windowMs)
	estimate := s.prevCount*(1-elapsedFraction) + s.currCount

	if estimate >= sw.limit {
		return false, estimate, 0
	}

	s.currCount++
	newEstimate := s.prevCount*(1-elapsedFraction) + s.currCount
	remaining := int(math.Max(0, sw.limit-newEstimate))
	return true, newEstimate, remaining
}

func (sw *SlidingWindowCounter) Estimate(key string) (float64, float64) {
	s := sw.getState(key)
	s.mu.Lock()
	defer s.mu.Unlock()

	now := time.Now().UnixMilli()
	windowStart := now - (now % sw.windowMs)

	if s.windowStart < windowStart {
		return 0, float64(now-windowStart) / float64(sw.windowMs)
	}

	elapsed := float64(now-s.windowStart) / float64(sw.windowMs)
	estimate := s.prevCount*(1-elapsed) + s.currCount
	return estimate, elapsed
}

// ─────────────────────────────────────────────────────────────────────────────
// Approximation error analysis
// ─────────────────────────────────────────────────────────────────────────────

// simulateApproximationError shows how the weighted formula behaves when the
// previous window had a non-uniform distribution. Worst case: prev window was
// completely full (all limit requests at t=0), and we're 50% into curr window.
// Expected over-count = limit × 0.5 = limit/2.
func simulateApproximationError(limit int, window time.Duration) {
	fmt.Println("\n── Approximation Error Analysis ──")
	fmt.Printf("  Assumption: requests were evenly spread across prev window.\n")
	fmt.Printf("  Reality: if all prev requests came at second=0, error grows.\n\n")

	sw := NewSlidingWindowCounter(limit, window)
	const key = "error-analysis"

	// Fill previous window completely
	for i := 0; i < limit; i++ {
		sw.Allow(key)
	}

	// Let half the window pass
	time.Sleep(window / 2)

	// Now the formula thinks prev contributes: limit × 0.5 = limit/2
	est, elapsed := sw.Estimate(key)
	fmt.Printf("  After %s (%.0f%% into new window):\n", window/2, elapsed*100)
	fmt.Printf("  Formula estimate = %.1f (prev=%d × %.2f + curr=0)\n",
		est, limit, 1-elapsed)
	fmt.Printf("  Available ≈ %d slots (limit %d - estimate %.1f)\n",
		int(math.Max(0, float64(limit)-est)), limit, est)
}

// ─────────────────────────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────────────────────────

func main() {
	fmt.Println("════════════════════════════════════════════")
	fmt.Println("   SLIDING WINDOW COUNTER — Go Demo         ")
	fmt.Println("════════════════════════════════════════════")

	// ── Part 1: Sequential behaviour with window rollover ─────────────────────
	fmt.Println("\n── Part 1: Window rollover (limit=10, window=500ms) ──")
	sw := NewSlidingWindowCounter(10, 500*time.Millisecond)

	fmt.Println("  Window 1: send 8 requests")
	for i := 1; i <= 8; i++ {
		ok, est, rem := sw.Allow("alice")
		fmt.Printf("    Req %2d: %s  estimate=%.2f  remaining≈%d\n",
			i, map[bool]string{true: "ALLOWED ✓", false: "REJECTED ✗"}[ok], est, rem)
	}

	// Wait for full rollover
	fmt.Println("\n  Sleeping 600ms (window rolls over, prev=8)...")
	time.Sleep(600 * time.Millisecond)

	fmt.Println("\n  Window 2: prev=8, ~60% elapsed → available ≈ 10 - 8×0.4 = 6.8")
	for i := 1; i <= 5; i++ {
		ok, est, rem := sw.Allow("alice")
		_, elapsed := sw.Estimate("alice")
		fmt.Printf("    Req %2d: %s  estimate=%.2f  elapsedFraction=%.2f  remaining≈%d\n",
			i, map[bool]string{true: "ALLOWED ✓", false: "REJECTED ✗"}[ok], est, elapsed, rem)
	}

	// ── Part 2: Race condition — UNSAFE ───────────────────────────────────────
	fmt.Println("\n── Part 2: Race condition — UNSAFE (limit=5, 30 goroutines) ──")

	for trial := 1; trial <= 3; trial++ {
		unsafe := NewUnsafeSlidingWindowCounter(5, 10*time.Second)
		var allowed int64
		var wg sync.WaitGroup
		gate := make(chan struct{})

		for i := 0; i < 30; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				<-gate
				if unsafe.Allow("race") {
					atomic.AddInt64(&allowed, 1)
				}
			}()
		}
		close(gate)
		wg.Wait()
		fmt.Printf("  Trial %d: %d allowed (should be ≤5; races inflate count)\n", trial, allowed)
	}

	// ── Part 3: Safe concurrent requests ─────────────────────────────────────
	fmt.Println("\n── Part 3: SAFE — 30 goroutines, limit=5 ──")

	for trial := 1; trial <= 3; trial++ {
		safe := NewSlidingWindowCounter(5, 10*time.Second)
		var allowed int64
		var wg sync.WaitGroup
		gate := make(chan struct{})

		for i := 0; i < 30; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				<-gate
				ok, _, _ := safe.Allow("safe")
				if ok {
					atomic.AddInt64(&allowed, 1)
				}
			}()
		}
		close(gate)
		wg.Wait()
		fmt.Printf("  Trial %d: %d allowed (always exactly 5)\n", trial, allowed)
	}

	// ── Part 4: Background ticker simulating real traffic ────────────────────
	fmt.Println("\n── Part 4: Background goroutine sending 20 req/s for 1s (limit=10/500ms) ──")

	sw2 := NewSlidingWindowCounter(10, 500*time.Millisecond)
	var totalSent, totalAllowed, totalRejected int64
	var wg sync.WaitGroup

	ticker := time.NewTicker(50 * time.Millisecond) // 20 req/s
	stop := time.After(1 * time.Second)

loop:
	for {
		select {
		case <-ticker.C:
			wg.Add(1)
			go func() {
				defer wg.Done()
				atomic.AddInt64(&totalSent, 1)
				ok, est, _ := sw2.Allow("ticker-test")
				if ok {
					atomic.AddInt64(&totalAllowed, 1)
					_ = est
				} else {
					atomic.AddInt64(&totalRejected, 1)
				}
			}()
		case <-stop:
			break loop
		}
	}
	ticker.Stop()
	wg.Wait()

	fmt.Printf("  Sent: %d | Allowed: %d | Rejected: %d\n",
		totalSent, totalAllowed, totalRejected)
	fmt.Printf("  At 20 req/s with limit=10/500ms (~20/s), roughly half should pass.\n")

	// ── Part 5: Approximation error ───────────────────────────────────────────
	simulateApproximationError(10, 500*time.Millisecond)
}
