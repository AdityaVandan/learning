// Scale 7: Windowed Stream Deduplication
//
// For unbounded streams, you can't keep all seen IDs in memory forever.
// Solution: define a time/count window — deduplicate within the window.
//
// Two window types:
//   Tumbling window: fixed, non-overlapping intervals (e.g., 1 minute buckets)
//   Sliding window:  continuous, overlapping windows (e.g., "last 5 minutes")
//
// This is the pattern used in Flink, Spark Streaming, and Kafka Streams.

package main

import (
	"fmt"
	"sync"
	"time"
)

// ============================================================
// Event type
// ============================================================

type Event struct {
	ID        string
	Timestamp time.Time
	Payload   string
}

// ============================================================
// Approach 1: Tumbling Window Dedup
//
// Divide time into fixed, non-overlapping buckets.
// Each bucket maintains its own seen-set.
// When a bucket expires, discard its state.
//
// Tradeoff: an event at 00:00:59 and its duplicate at 00:01:01 may both pass through
// (they're in different windows). Acceptable for most analytics use cases.
// ============================================================

type TumblingWindowDedup struct {
	windowSize time.Duration
	mu         sync.Mutex
	buckets    map[int64]map[string]bool // bucket_id → seen IDs
}

func NewTumblingWindowDedup(windowSize time.Duration) *TumblingWindowDedup {
	d := &TumblingWindowDedup{
		windowSize: windowSize,
		buckets:    make(map[int64]map[string]bool),
	}
	go d.evictExpired()
	return d
}

func (d *TumblingWindowDedup) bucketID(t time.Time) int64 {
	return t.UnixNano() / d.windowSize.Nanoseconds()
}

func (d *TumblingWindowDedup) IsDuplicate(event Event) bool {
	d.mu.Lock()
	defer d.mu.Unlock()

	bID := d.bucketID(event.Timestamp)
	if _, exists := d.buckets[bID]; !exists {
		d.buckets[bID] = make(map[string]bool)
	}

	if d.buckets[bID][event.ID] {
		return true
	}
	d.buckets[bID][event.ID] = true
	return false
}

func (d *TumblingWindowDedup) evictExpired() {
	for {
		time.Sleep(d.windowSize)
		d.mu.Lock()
		currentBucket := d.bucketID(time.Now())
		for bID := range d.buckets {
			if bID < currentBucket-1 { // keep current + previous bucket
				delete(d.buckets, bID)
			}
		}
		d.mu.Unlock()
	}
}

func (d *TumblingWindowDedup) Stats() {
	d.mu.Lock()
	defer d.mu.Unlock()
	totalKeys := 0
	for _, b := range d.buckets {
		totalKeys += len(b)
	}
	fmt.Printf("  Tumbling window: %d active buckets, %d total tracked IDs\n",
		len(d.buckets), totalKeys)
}

// ============================================================
// Approach 2: Sliding Window Dedup
//
// Keep a time-ordered ring buffer of (timestamp, id) pairs.
// For each new event: evict entries older than the window, then check for duplicates.
//
// This is more accurate (no bucket boundary problem) but uses more memory.
// Memory usage is bounded by: max_events_per_window * (ID_size + timestamp_size)
// ============================================================

type entry struct {
	id        string
	arrivedAt time.Time
}

type SlidingWindowDedup struct {
	windowSize time.Duration
	mu         sync.RWMutex
	entries    []entry      // ordered ring of recent entries
	seen       map[string]int // id → count of occurrences in window
}

func NewSlidingWindowDedup(windowSize time.Duration) *SlidingWindowDedup {
	return &SlidingWindowDedup{
		windowSize: windowSize,
		seen:       make(map[string]int),
	}
}

func (d *SlidingWindowDedup) evictOld(now time.Time) {
	cutoff := now.Add(-d.windowSize)
	i := 0
	for i < len(d.entries) && d.entries[i].arrivedAt.Before(cutoff) {
		id := d.entries[i].id
		d.seen[id]--
		if d.seen[id] == 0 {
			delete(d.seen, id)
		}
		i++
	}
	d.entries = d.entries[i:]
}

func (d *SlidingWindowDedup) IsDuplicate(event Event) bool {
	d.mu.Lock()
	defer d.mu.Unlock()

	now := time.Now()
	d.evictOld(now)

	if d.seen[event.ID] > 0 {
		return true
	}

	d.entries = append(d.entries, entry{id: event.ID, arrivedAt: now})
	d.seen[event.ID]++
	return false
}

func (d *SlidingWindowDedup) WindowSize() int {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return len(d.seen)
}

// ============================================================
// Approach 3: Count-Based Window Dedup
//
// Deduplicate within the last N events (not time-based).
// Useful when event rate is highly variable.
// ============================================================

type CountWindowDedup struct {
	maxSize int
	mu      sync.Mutex
	ring    []string
	pos     int
	seen    map[string]int
}

func NewCountWindowDedup(maxSize int) *CountWindowDedup {
	return &CountWindowDedup{
		maxSize: maxSize,
		ring:    make([]string, maxSize),
		seen:    make(map[string]int),
	}
}

func (d *CountWindowDedup) IsDuplicate(id string) bool {
	d.mu.Lock()
	defer d.mu.Unlock()

	if d.seen[id] > 0 {
		return true
	}

	// Evict the oldest entry (ring buffer position)
	oldID := d.ring[d.pos]
	if oldID != "" {
		d.seen[oldID]--
		if d.seen[oldID] == 0 {
			delete(d.seen, oldID)
		}
	}

	d.ring[d.pos] = id
	d.seen[id]++
	d.pos = (d.pos + 1) % d.maxSize
	return false
}

// ============================================================
// Approach 4: Multi-stage pipeline (Bloom + exact confirmation)
//
// Stage 1: Bloom filter — fast O(1) pre-filter, eliminates ~99% of non-duplicates
// Stage 2: Redis SET NX — exact confirmation for bloom positives
//
// This is the production pattern for very high throughput systems.
// ============================================================

// Simulated version of the two-stage pipeline
type TwoStageDedup struct {
	bloom    *BloomFilter
	exact    map[string]bool
	bloomHit int
	exactHit int
	mu       sync.Mutex
}

type BloomFilter struct {
	bits    []uint64
	numBits uint
	numHash uint
	count   uint
}

func newSimpleBloom(n uint) *BloomFilter {
	m := n * 10 // ~10 bits per item for ~1% FP rate
	words := (m + 63) / 64
	return &BloomFilter{bits: make([]uint64, words), numBits: words * 64, numHash: 7}
}

func (bf *BloomFilter) hash(key string, seed uint) uint {
	h := uint(14695981039346656037)
	for _, c := range []byte(key) {
		h ^= uint(c)
		h *= 1099511628211
	}
	return (h ^ (h >> 17) ^ uint(seed)*2654435761) % bf.numBits
}

func (bf *BloomFilter) Add(key string) {
	for i := uint(0); i < bf.numHash; i++ {
		pos := bf.hash(key, i)
		bf.bits[pos/64] |= 1 << (pos % 64)
	}
	bf.count++
}

func (bf *BloomFilter) MightContain(key string) bool {
	for i := uint(0); i < bf.numHash; i++ {
		pos := bf.hash(key, i)
		if bf.bits[pos/64]&(1<<(pos%64)) == 0 {
			return false
		}
	}
	return true
}

func NewTwoStageDedup(expectedItems uint) *TwoStageDedup {
	return &TwoStageDedup{
		bloom: newSimpleBloom(expectedItems),
		exact: make(map[string]bool),
	}
}

func (d *TwoStageDedup) IsDuplicate(id string) bool {
	d.mu.Lock()
	defer d.mu.Unlock()

	// Stage 1: Bloom filter (extremely fast, no false negatives)
	if !d.bloom.MightContain(id) {
		// Definitely not a duplicate
		d.bloom.Add(id)
		d.exact[id] = true
		return false
	}

	d.bloomHit++

	// Stage 2: Exact check (only reached for ~1% of non-duplicates + all real duplicates)
	if d.exact[id] {
		d.exactHit++
		return true
	}

	// Bloom false positive — not actually a duplicate
	d.exact[id] = true
	return false
}

// ============================================================
// Main
// ============================================================

func main() {
	fmt.Println("=== Approach 1: Tumbling Window ===")
	tumbling := NewTumblingWindowDedup(200 * time.Millisecond)

	now := time.Now()
	events := []struct {
		event Event
		sleep time.Duration
	}{
		{Event{ID: "e1", Timestamp: now, Payload: "click"}, 0},
		{Event{ID: "e2", Timestamp: now, Payload: "view"}, 0},
		{Event{ID: "e1", Timestamp: now, Payload: "click"}, 0}, // dup within window
		{Event{ID: "e3", Timestamp: now, Payload: "buy"}, 0},
	}

	for _, e := range events {
		isDup := tumbling.IsDuplicate(e.event)
		status := "processed"
		if isDup {
			status = "SKIPPED (duplicate)"
		}
		fmt.Printf("  %s at t+0ms: %s\n", e.event.ID, status)
	}
	tumbling.Stats()

	fmt.Println("\nWaiting for window to expire (220ms)...")
	time.Sleep(220 * time.Millisecond)

	// After window expiry, same IDs should be accepted again
	for _, id := range []string{"e1", "e2"} {
		e := Event{ID: id, Timestamp: time.Now(), Payload: "replay"}
		isDup := tumbling.IsDuplicate(e)
		fmt.Printf("  %s after window expiry: duplicate=%v\n", id, isDup)
	}

	fmt.Println("\n=== Approach 2: Sliding Window ===")
	sliding := NewSlidingWindowDedup(150 * time.Millisecond)

	testEvents := []Event{
		{ID: "s1"}, {ID: "s2"}, {ID: "s1"}, {ID: "s3"},
	}

	for _, e := range testEvents {
		isDup := sliding.IsDuplicate(e)
		fmt.Printf("  %s: duplicate=%v (window size: %d)\n", e.ID, isDup, sliding.WindowSize())
	}

	fmt.Println("Waiting 160ms (window expires)...")
	time.Sleep(160 * time.Millisecond)

	for _, id := range []string{"s1", "s2"} {
		e := Event{ID: id}
		isDup := sliding.IsDuplicate(e)
		fmt.Printf("  %s after window: duplicate=%v\n", id, isDup)
	}

	fmt.Println("\n=== Approach 3: Count-Based Window (last 3 events) ===")
	countWindow := NewCountWindowDedup(3)

	sequence := []string{"a", "b", "c", "a", "d", "a", "b"}
	for _, id := range sequence {
		isDup := countWindow.IsDuplicate(id)
		status := "new"
		if isDup {
			status = "DUP"
		}
		fmt.Printf("  Event '%s': %s\n", id, status)
	}

	fmt.Println("\n=== Approach 4: Two-Stage Bloom + Exact (high throughput) ===")
	twoStage := NewTwoStageDedup(1000)

	ids := []string{"a", "b", "c", "a", "d", "b", "e", "a", "f", "c"}
	processed, duped := 0, 0
	for _, id := range ids {
		if twoStage.IsDuplicate(id) {
			duped++
			fmt.Printf("  [DUP]  %s\n", id)
		} else {
			processed++
			fmt.Printf("  [NEW]  %s\n", id)
		}
	}
	fmt.Printf("\nProcessed: %d, Duplicates: %d\n", processed, duped)
	fmt.Printf("Bloom filter hits (potential dups): %d\n", twoStage.bloomHit)
	fmt.Printf("Exact hits (confirmed dups):        %d\n", twoStage.exactHit)

	fmt.Println("\n=== Memory Bounds Comparison ===")
	type windowConfig struct {
		name        string
		maxItems    int
		bytesPerItem int
	}
	configs := []windowConfig{
		{"Hash set (unbounded)", 10_000_000, 50},
		{"Tumbling window (1min, 10k events/min)", 10_000, 50},
		{"Sliding window (5min, 10k events/min)", 50_000, 70},
		{"Count window (last 100k)", 100_000, 50},
		{"Bloom filter (1M items, 1% FP)", 1_000_000, 1},
	}
	fmt.Printf("%-50s %10s\n", "Strategy", "Memory")
	for _, c := range configs {
		bytes := c.maxItems * c.bytesPerItem
		var mem string
		if bytes < 1024*1024 {
			mem = fmt.Sprintf("%.1f KB", float64(bytes)/1024)
		} else {
			mem = fmt.Sprintf("%.1f MB", float64(bytes)/1024/1024)
		}
		fmt.Printf("%-50s %10s\n", c.name, mem)
	}
}
