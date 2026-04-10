// Scale 4: Distributed Deduplication with Redis
//
// Redis SET NX (Set if Not eXists) is the canonical distributed dedup primitive.
// It's atomic, O(1), and supports TTL for automatic expiry.
//
// Pattern:
//   1. Attempt: SET dedup:<event_id> 1 NX EX <ttl_seconds>
//   2. If SET succeeds → first time seeing this event → process it
//   3. If SET fails (key exists) → duplicate → skip it
//
// Run: docker run -p 6379:6379 redis:alpine
// Then: go run main.go

package main

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// --- Mock Redis client (so the code runs without a real Redis instance) ---
// Replace with: github.com/redis/go-redis/v9 in production

type MockRedis struct {
	mu      sync.Mutex
	store   map[string]time.Time // key → expiry time
}

func NewMockRedis() *MockRedis {
	r := &MockRedis{store: make(map[string]time.Time)}
	go r.expireLoop()
	return r
}

// SetNX sets key with TTL if it doesn't exist. Returns true if set, false if already exists.
func (r *MockRedis) SetNX(ctx context.Context, key string, ttl time.Duration) (bool, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	expiry, exists := r.store[key]
	if exists && time.Now().Before(expiry) {
		return false, nil // key exists and not expired
	}
	r.store[key] = time.Now().Add(ttl)
	return true, nil
}

func (r *MockRedis) expireLoop() {
	for {
		time.Sleep(100 * time.Millisecond)
		r.mu.Lock()
		now := time.Now()
		for k, exp := range r.store {
			if now.After(exp) {
				delete(r.store, k)
			}
		}
		r.mu.Unlock()
	}
}

func (r *MockRedis) Size() int {
	r.mu.Lock()
	defer r.mu.Unlock()
	return len(r.store)
}

// ---- Production Redis version (commented out) ----
//
// import "github.com/redis/go-redis/v9"
//
// rdb := redis.NewClient(&redis.Options{Addr: "localhost:6379"})
//
// func SetNX(ctx context.Context, key string, ttl time.Duration) (bool, error) {
//     return rdb.SetNX(ctx, key, 1, ttl).Result()
// }

// --- Deduplicator wraps Redis with domain logic ---

type Deduplicator struct {
	redis  *MockRedis
	prefix string
	ttl    time.Duration
}

func NewDeduplicator(redis *MockRedis, prefix string, ttl time.Duration) *Deduplicator {
	return &Deduplicator{redis: redis, prefix: prefix, ttl: ttl}
}

// IsDuplicate returns true if this event has been seen within the TTL window.
func (d *Deduplicator) IsDuplicate(ctx context.Context, eventID string) (bool, error) {
	key := d.prefix + eventID
	set, err := d.redis.SetNX(ctx, key, d.ttl)
	if err != nil {
		// On Redis failure, decide your policy:
		//   - fail open  (return false = process the event, risk duplicates)
		//   - fail closed (return true = skip the event, risk data loss)
		// For financial transactions: fail closed. For analytics: fail open.
		return false, fmt.Errorf("redis error: %w", err)
	}
	return !set, nil // set=true means first time → NOT a duplicate
}

// --- Event processor using the deduplicator ---

type EventProcessor struct {
	dedup     *Deduplicator
	processed int
	skipped   int
	mu        sync.Mutex
}

func NewEventProcessor(dedup *Deduplicator) *EventProcessor {
	return &EventProcessor{dedup: dedup}
}

type Event struct {
	ID      string
	Type    string
	Payload string
}

func (ep *EventProcessor) Process(ctx context.Context, event Event) error {
	isDup, err := ep.dedup.IsDuplicate(ctx, event.ID)
	if err != nil {
		return err
	}
	if isDup {
		ep.mu.Lock()
		ep.skipped++
		ep.mu.Unlock()
		fmt.Printf("  [SKIP] %s (duplicate)\n", event.ID)
		return nil
	}

	// Simulate processing
	ep.mu.Lock()
	ep.processed++
	ep.mu.Unlock()
	fmt.Printf("  [PROC] %s: %s - %s\n", event.ID, event.Type, event.Payload)
	return nil
}

// --- Idempotency key pattern for API/RPC calls ---
// This is what payment processors (Stripe, Razorpay) do.

type IdempotencyStore struct {
	mu      sync.Mutex
	results map[string]IdempotentResult
}

type IdempotentResult struct {
	StatusCode int
	Body       string
	CreatedAt  time.Time
}

func NewIdempotencyStore() *IdempotencyStore {
	return &IdempotencyStore{results: make(map[string]IdempotentResult)}
}

// Execute runs fn only if this idempotency key hasn't been seen.
// On duplicate, returns the cached result from the first execution.
func (s *IdempotencyStore) Execute(
	idempotencyKey string,
	fn func() IdempotentResult,
) (IdempotentResult, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if cached, exists := s.results[idempotencyKey]; exists {
		return cached, true // true = was a duplicate, returning cached response
	}

	result := fn()
	s.results[idempotencyKey] = result
	return result, false
}

// --- Concurrent dedup stress test ---
// Demonstrates that with Redis SET NX, only one goroutine "wins" per event ID.

func concurrentDedupTest(dedup *Deduplicator) {
	ctx := context.Background()
	const numGoroutines = 10
	const eventID = "concurrent_event_001"

	wins := 0
	var mu sync.Mutex
	var wg sync.WaitGroup

	for i := 0; i < numGoroutines; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()

			isDup, _ := dedup.IsDuplicate(ctx, eventID)
			if !isDup {
				mu.Lock()
				wins++
				mu.Unlock()
				fmt.Printf("    Goroutine %d WON the race for %s\n", id, eventID)
			}
		}(i)
	}

	wg.Wait()
	fmt.Printf("  %d/%d goroutines processed the event (expected: 1)\n", wins, numGoroutines)
}

func main() {
	ctx := context.Background()
	redis := NewMockRedis()

	fmt.Println("=== Basic Deduplication with Redis SET NX ===")
	dedup := NewDeduplicator(redis, "dedup:events:", 5*time.Second)
	processor := NewEventProcessor(dedup)

	events := []Event{
		{ID: "evt_001", Type: "payment", Payload: "$100 to Bob"},
		{ID: "evt_002", Type: "login",   Payload: "user alice"},
		{ID: "evt_001", Type: "payment", Payload: "$100 to Bob"},   // retry/duplicate
		{ID: "evt_003", Type: "signup",  Payload: "user carol"},
		{ID: "evt_002", Type: "login",   Payload: "user alice"},    // duplicate
		{ID: "evt_004", Type: "payment", Payload: "$50 to Dave"},
		{ID: "evt_001", Type: "payment", Payload: "$100 to Bob"},   // another retry
	}

	for _, e := range events {
		processor.Process(ctx, e)
	}
	fmt.Printf("\nResult: %d processed, %d skipped\n", processor.processed, processor.skipped)
	fmt.Printf("Redis keys in use: %d\n", redis.Size())

	fmt.Println("\n=== TTL Expiry (sliding window dedup) ===")
	shortDedup := NewDeduplicator(redis, "dedup:short:", 300*time.Millisecond)

	fmt.Println("First attempt:")
	isDup, _ := shortDedup.IsDuplicate(ctx, "ttl_test")
	fmt.Printf("  Is duplicate: %v (expected: false)\n", isDup)

	fmt.Println("Immediate retry:")
	isDup, _ = shortDedup.IsDuplicate(ctx, "ttl_test")
	fmt.Printf("  Is duplicate: %v (expected: true)\n", isDup)

	fmt.Println("Waiting for TTL to expire...")
	time.Sleep(350 * time.Millisecond)

	fmt.Println("Attempt after TTL expiry:")
	isDup, _ = shortDedup.IsDuplicate(ctx, "ttl_test")
	fmt.Printf("  Is duplicate: %v (expected: false — key has expired)\n", isDup)

	fmt.Println("\n=== Idempotency Key Pattern (API call dedup) ===")
	store := NewIdempotencyStore()
	callCount := 0

	processPayment := func(idempotencyKey, amount, recipient string) {
		result, wasDuplicate := store.Execute(idempotencyKey, func() IdempotentResult {
			callCount++
			fmt.Printf("  Executing payment: %s to %s\n", amount, recipient)
			// Simulate DB write, external API call, etc.
			return IdempotentResult{
				StatusCode: 200,
				Body:       fmt.Sprintf(`{"status":"ok","txn_id":"txn_%d"}`, callCount),
				CreatedAt:  time.Now(),
			}
		})

		if wasDuplicate {
			fmt.Printf("  Duplicate request (key=%s) — returning cached response: %s\n",
				idempotencyKey, result.Body)
		} else {
			fmt.Printf("  Response: %s\n", result.Body)
		}
	}

	fmt.Println("Client sends payment request:")
	processPayment("idem_key_abc123", "$200", "Eve")
	fmt.Println("Network timeout, client retries with same key:")
	processPayment("idem_key_abc123", "$200", "Eve")
	fmt.Println("Client retries again:")
	processPayment("idem_key_abc123", "$200", "Eve")
	fmt.Println("Different payment, different key:")
	processPayment("idem_key_xyz999", "$50", "Frank")
	fmt.Printf("\nActual payment executions: %d (not 3)\n", callCount)

	fmt.Println("\n=== Concurrent Race Condition Test ===")
	fmt.Println("10 goroutines all trying to process the same event simultaneously:")
	concurrentDedupTest(dedup)

	fmt.Println("\n=== Key Design Patterns ===")
	fmt.Println("Good dedup key design:")
	examples := []struct {
		usecase string
		key     string
	}{
		{"Payment retry", "dedup:payment:<txn_id>"},
		{"Webhook delivery", "dedup:webhook:<webhook_id>:<attempt_num>"},
		{"Email dedup (24h window)", "dedup:email:<user_id>:<template_id>:<date>"},
		{"Event processing", "dedup:event:<source>:<event_id>"},
		{"API idempotency", "idem:<api_version>:<idempotency_key>"},
	}
	for _, e := range examples {
		fmt.Printf("  %-35s → %s\n", e.usecase, e.key)
	}
}
