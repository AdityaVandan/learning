// LEAKY BUCKET — Go implementation
//
// Run:  go run ./leaky-bucket/
// Race: go run -race ./leaky-bucket/
//
// Key Go concepts demonstrated:
//   - Buffered channel as the bucket queue (idiomatic Go)
//   - Goroutine as the drip processor using time.Ticker
//   - sync.Mutex for the counter-based variant
//   - sync.WaitGroup to coordinate concurrent senders
//   - done channel for clean shutdown (context cancellation pattern)
package main

import (
	"fmt"
	"sync"
	"sync/atomic"
	"time"
)

// ─────────────────────────────────────────────────────────────────────────────
// CLASSICAL Leaky Bucket — buffered channel as queue, goroutine as drip
//
// This is idiomatic Go: a buffered channel naturally provides the fixed-size
// queue. Sending to a full channel would block, so we use a non-blocking
// select to detect overflow (reject) instead.
// ─────────────────────────────────────────────────────────────────────────────

type Request struct {
	id     int
	result chan bool // goroutine sends true back here when processed
}

type LeakyBucketClassical struct {
	queue  chan Request      // buffered channel = bucket of capacity N
	ticker *time.Ticker     // drip rate: one request processed per tick
	done   chan struct{}     // shutdown signal
}

func NewLeakyBucketClassical(capacity int, leakInterval time.Duration) *LeakyBucketClassical {
	lb := &LeakyBucketClassical{
		queue:  make(chan Request, capacity), // capacity IS the buffer size
		ticker: time.NewTicker(leakInterval),
		done:   make(chan struct{}),
	}
	go lb.drip() // start the processor goroutine
	return lb
}

// drip runs in its own goroutine, processing one request per tick.
// This is the "leak" — requests flow out at a controlled, constant rate.
func (lb *LeakyBucketClassical) drip() {
	for {
		select {
		case <-lb.done:
			return
		case <-lb.ticker.C:
			select {
			case req := <-lb.queue:
				req.result <- true // process the oldest request (FIFO)
			default:
				// Queue empty — nothing to process this tick
			}
		}
	}
}

// Enqueue tries to add a request to the bucket.
// Returns a channel the caller can block on to wait for processing.
// If the bucket is full, returns nil immediately (overflow/reject).
func (lb *LeakyBucketClassical) Enqueue(id int) chan bool {
	result := make(chan bool, 1)
	req := Request{id: id, result: result}

	// Non-blocking send: if channel is full → overflow → reject
	select {
	case lb.queue <- req:
		return result // caller waits on this channel
	default:
		return nil // bucket full, rejected
	}
}

func (lb *LeakyBucketClassical) Stop() {
	lb.ticker.Stop()
	close(lb.done)
}

func (lb *LeakyBucketClassical) QueueDepth() int {
	return len(lb.queue)
}

// ─────────────────────────────────────────────────────────────────────────────
// UNSAFE counter variant — shows race condition without mutex
// ─────────────────────────────────────────────────────────────────────────────

type UnsafeLeakyBucketCounter struct {
	level          float64
	capacity       float64
	leakRatePerSec float64
	lastLeak       time.Time
}

func NewUnsafeLeakyCounter(capacity, leakRate float64) *UnsafeLeakyBucketCounter {
	return &UnsafeLeakyBucketCounter{
		capacity:       capacity,
		leakRatePerSec: leakRate,
		lastLeak:       time.Now(),
	}
}

func (lb *UnsafeLeakyBucketCounter) Allow() bool {
	now := time.Now()
	elapsed := now.Sub(lb.lastLeak).Seconds()
	lb.lastLeak = now

	leaked := elapsed * lb.leakRatePerSec
	if lb.level-leaked < 0 {
		lb.level = 0
	} else {
		lb.level -= leaked
	}
	// ← two goroutines can both see level < capacity here
	if lb.level+1 > lb.capacity {
		return false
	}
	lb.level++ // ← both increment, driving level over capacity
	return true
}

// ─────────────────────────────────────────────────────────────────────────────
// SAFE counter variant — mutex protected
// ─────────────────────────────────────────────────────────────────────────────

type LeakyBucketCounter struct {
	mu             sync.Mutex
	level          float64
	capacity       float64
	leakRatePerSec float64
	lastLeak       time.Time
}

func NewLeakyBucketCounter(capacity, leakRate float64) *LeakyBucketCounter {
	return &LeakyBucketCounter{
		capacity:       capacity,
		leakRatePerSec: leakRate,
		lastLeak:       time.Now(),
	}
}

func (lb *LeakyBucketCounter) Allow() bool {
	lb.mu.Lock()
	defer lb.mu.Unlock()

	now := time.Now()
	elapsed := now.Sub(lb.lastLeak).Seconds()
	lb.lastLeak = now

	leaked := elapsed * lb.leakRatePerSec
	lb.level = max(0, lb.level-leaked)

	if lb.level+1 > lb.capacity {
		return false
	}
	lb.level++
	return true
}

func (lb *LeakyBucketCounter) Level() float64 {
	lb.mu.Lock()
	defer lb.mu.Unlock()
	return lb.level
}

func max(a, b float64) float64 {
	if a > b {
		return a
	}
	return b
}

// ─────────────────────────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────────────────────────

func main() {
	fmt.Println("════════════════════════════════════════════")
	fmt.Println("         LEAKY BUCKET — Go Demo             ")
	fmt.Println("════════════════════════════════════════════")

	// ── Part 1: Classical queue — burst arrives, dripped out smoothly ─────────
	fmt.Println("\n── Part 1: Classical Queue (capacity=3, drip every 200ms) ──")
	fmt.Println("  10 goroutines fire simultaneously; only 3 can queue, rest overflow")

	lb := NewLeakyBucketClassical(3, 200*time.Millisecond)
	var wg sync.WaitGroup
	start := make(chan struct{}) // synchronised start gate
	var queued, overflowed int64

	for i := 1; i <= 10; i++ {
		wg.Add(1)
		id := i
		go func() {
			defer wg.Done()
			<-start // all goroutines released at once

			ch := lb.Enqueue(id)
			if ch == nil {
				atomic.AddInt64(&overflowed, 1)
				fmt.Printf("  Req %2d: OVERFLOW (bucket full)\n", id)
				return
			}
			atomic.AddInt64(&queued, 1)
			// Block until drip processor handles this request
			<-ch
			fmt.Printf("  Req %2d: PROCESSED (dripped out at %s)\n", id, time.Now().Format("15:04:05.000"))
		}()
	}

	close(start) // fire all goroutines simultaneously
	wg.Wait()
	lb.Stop()

	fmt.Printf("\n  Summary: %d queued+processed, %d overflowed\n", queued, overflowed)

	// ── Part 2: Smooth output rate demo ──────────────────────────────────────
	fmt.Println("\n── Part 2: Output smoothing (capacity=10, drip every 100ms) ──")
	fmt.Println("  All 10 requests enqueued at t=0, observe smooth 100ms spacing:")

	lb2 := NewLeakyBucketClassical(10, 100*time.Millisecond)
	var wg2 sync.WaitGroup
	start2 := make(chan struct{})
	t0 := time.Now()

	for i := 1; i <= 10; i++ {
		wg2.Add(1)
		id := i
		go func() {
			defer wg2.Done()
			<-start2
			ch := lb2.Enqueue(id)
			if ch != nil {
				<-ch
				fmt.Printf("  Req %2d processed at +%dms\n", id, time.Since(t0).Milliseconds())
			}
		}()
	}
	close(start2)
	wg2.Wait()
	lb2.Stop()

	// ── Part 3: Race condition in counter variant ────────────────────────────
	fmt.Println("\n── Part 3: Counter variant — UNSAFE vs SAFE (capacity=5) ──")

	fmt.Println("\n  UNSAFE (no mutex) — 20 goroutines, capacity=5:")
	for trial := 1; trial <= 3; trial++ {
		unsafe := NewUnsafeLeakyCounter(5, 0)
		var allowedCount int64
		var wg3 sync.WaitGroup
		gate := make(chan struct{})
		for j := 0; j < 20; j++ {
			wg3.Add(1)
			go func() {
				defer wg3.Done()
				<-gate
				if unsafe.Allow() {
					atomic.AddInt64(&allowedCount, 1)
				}
			}()
		}
		close(gate)
		wg3.Wait()
		fmt.Printf("    Trial %d: allowed=%d (should be ≤5, races cause over-counting)\n",
			trial, allowedCount)
	}

	fmt.Println("\n  SAFE (sync.Mutex) — 20 goroutines, capacity=5:")
	for trial := 1; trial <= 3; trial++ {
		safe := NewLeakyBucketCounter(5, 0)
		var allowedCount int64
		var wg4 sync.WaitGroup
		gate := make(chan struct{})
		for j := 0; j < 20; j++ {
			wg4.Add(1)
			go func() {
				defer wg4.Done()
				<-gate
				if safe.Allow() {
					atomic.AddInt64(&allowedCount, 1)
				}
			}()
		}
		close(gate)
		wg4.Wait()
		fmt.Printf("    Trial %d: allowed=%d (always exactly 5)\n", trial, allowedCount)
	}

	// ── Part 4: Drain over time ───────────────────────────────────────────────
	fmt.Println("\n── Part 4: Counter drain over time (capacity=5, drain=5/sec) ──")
	counter := NewLeakyBucketCounter(5, 5)

	for i := 1; i <= 5; i++ {
		ok := counter.Allow()
		fmt.Printf("  Req %d: %v  level=%.1f\n", i, map[bool]string{true: "ALLOWED ✓", false: "REJECTED ✗"}[ok], counter.Level())
	}
	// 6th should fail
	ok := counter.Allow()
	fmt.Printf("  Req 6: %v  level=%.1f\n", map[bool]string{true: "ALLOWED ✓", false: "REJECTED ✗"}[ok], counter.Level())

	fmt.Println("\n  Sleeping 1s (5 units drain out)...")
	time.Sleep(time.Second)

	for i := 7; i <= 9; i++ {
		ok := counter.Allow()
		fmt.Printf("  Req %d: %v  level=%.1f\n", i, map[bool]string{true: "ALLOWED ✓", false: "REJECTED ✗"}[ok], counter.Level())
	}
}
