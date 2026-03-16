// Scale 5: Database-Level Deduplication
//
// PostgreSQL (and most SQL databases) provide two mechanisms:
//   1. UNIQUE constraints with INSERT ... ON CONFLICT DO NOTHING / UPDATE
//   2. Idempotency key tables for RPC/API-level dedup
//
// This file shows the patterns with runnable mock implementations.
// Replace MockDB with real *sql.DB + lib/pq for production.
//
// Real connection:
//   db, err := sql.Open("postgres", "host=localhost user=postgres dbname=dedup sslmode=disable")

package main

import (
	"errors"
	"fmt"
	"sync"
	"time"
)

// ============================================================
// MockDB simulates PostgreSQL behavior for demonstration
// ============================================================

type MockDB struct {
	mu            sync.Mutex
	events        map[string]EventRow
	idempotency   map[string]IdempotencyRow
	processedTotal int
	conflictTotal  int
}

type EventRow struct {
	EventID   string
	UserID    string
	EventType string
	Payload   string
	CreatedAt time.Time
}

type IdempotencyRow struct {
	Key        string
	StatusCode int
	Response   string
	CreatedAt  time.Time
	ExpiresAt  time.Time
}

func NewMockDB() *MockDB {
	return &MockDB{
		events:      make(map[string]EventRow),
		idempotency: make(map[string]IdempotencyRow),
	}
}

var ErrConflict = errors.New("unique constraint violation")

// InsertEventIgnoreConflict simulates:
//   INSERT INTO events (event_id, user_id, event_type, payload)
//   VALUES ($1, $2, $3, $4)
//   ON CONFLICT (event_id) DO NOTHING
func (db *MockDB) InsertEventIgnoreConflict(row EventRow) (inserted bool, err error) {
	db.mu.Lock()
	defer db.mu.Unlock()

	if _, exists := db.events[row.EventID]; exists {
		db.conflictTotal++
		return false, nil // ON CONFLICT DO NOTHING
	}
	row.CreatedAt = time.Now()
	db.events[row.EventID] = row
	db.processedTotal++
	return true, nil
}

// InsertEventUpsert simulates:
//   INSERT INTO events (event_id, user_id, event_type, payload)
//   VALUES ($1, $2, $3, $4)
//   ON CONFLICT (event_id) DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()
func (db *MockDB) InsertEventUpsert(row EventRow) (isNew bool, err error) {
	db.mu.Lock()
	defer db.mu.Unlock()

	_, exists := db.events[row.EventID]
	row.CreatedAt = time.Now()
	db.events[row.EventID] = row // always overwrite
	return !exists, nil
}

// GetOrCreateIdempotencyRecord simulates:
//   WITH ins AS (
//     INSERT INTO idempotency_keys (key, expires_at)
//     VALUES ($1, NOW() + INTERVAL '24 hours')
//     ON CONFLICT (key) DO NOTHING
//     RETURNING key, true AS is_new
//   )
//   SELECT key, false AS is_new FROM idempotency_keys WHERE key = $1
//   UNION ALL SELECT key, is_new FROM ins
func (db *MockDB) GetOrCreateIdempotencyRecord(key string, ttl time.Duration) (row IdempotencyRow, isNew bool) {
	db.mu.Lock()
	defer db.mu.Unlock()

	if existing, exists := db.idempotency[key]; exists {
		if time.Now().Before(existing.ExpiresAt) {
			return existing, false
		}
		// expired — treat as new
		delete(db.idempotency, key)
	}

	row = IdempotencyRow{
		Key:       key,
		CreatedAt: time.Now(),
		ExpiresAt: time.Now().Add(ttl),
	}
	db.idempotency[key] = row
	return row, true
}

func (db *MockDB) UpdateIdempotencyResponse(key string, statusCode int, response string) {
	db.mu.Lock()
	defer db.mu.Unlock()
	if row, exists := db.idempotency[key]; exists {
		row.StatusCode = statusCode
		row.Response = response
		db.idempotency[key] = row
	}
}

// ============================================================
// Event dedup service
// ============================================================

type EventService struct {
	db *MockDB
}

func NewEventService(db *MockDB) *EventService {
	return &EventService{db: db}
}

// ProcessEvent implements exactly-once event processing.
// Even if called concurrently with the same event_id, only one will win.
func (s *EventService) ProcessEvent(eventID, userID, eventType, payload string) error {
	row := EventRow{
		EventID:   eventID,
		UserID:    userID,
		EventType: eventType,
		Payload:   payload,
	}

	inserted, err := s.db.InsertEventIgnoreConflict(row)
	if err != nil {
		return fmt.Errorf("db error: %w", err)
	}

	if !inserted {
		fmt.Printf("  [DEDUP] event_id=%s already processed, skipping\n", eventID)
		return nil
	}

	// Only reaches here once per unique event_id
	fmt.Printf("  [OK]    event_id=%s processed (type=%s)\n", eventID, eventType)
	return nil
}

// ============================================================
// Idempotency key service for API endpoints
// ============================================================

type APIService struct {
	db *MockDB
}

func NewAPIService(db *MockDB) *APIService {
	return &APIService{db: db}
}

type PaymentRequest struct {
	IdempotencyKey string
	Amount         float64
	Currency       string
	RecipientID    string
}

type PaymentResponse struct {
	TransactionID string
	Status        string
	Amount        float64
}

var txnCounter int

func (s *APIService) CreatePayment(req PaymentRequest) (PaymentResponse, error) {
	// Step 1: Try to claim this idempotency key in the database
	_, isNew := s.db.GetOrCreateIdempotencyRecord(req.IdempotencyKey, 24*time.Hour)

	if !isNew {
		// This key was already used — fetch and return the cached response
		s.db.mu.Lock()
		cached := s.db.idempotency[req.IdempotencyKey]
		s.db.mu.Unlock()

		if cached.Response != "" {
			fmt.Printf("  [CACHE] Returning cached response for key=%s\n", req.IdempotencyKey)
			return PaymentResponse{
				TransactionID: cached.Response,
				Status:        "ok (cached)",
				Amount:        req.Amount,
			}, nil
		}

		// Key exists but no response yet (still in flight) — return conflict
		return PaymentResponse{}, fmt.Errorf("request already in progress, retry later")
	}

	// Step 2: Process the payment (DB write, bank API call, etc.)
	txnCounter++
	txnID := fmt.Sprintf("txn_%06d", txnCounter)
	fmt.Printf("  [NEW]   Processing payment %.2f %s to %s → %s\n",
		req.Amount, req.Currency, req.RecipientID, txnID)

	// Step 3: Store the response against the idempotency key
	s.db.UpdateIdempotencyResponse(req.IdempotencyKey, 200, txnID)

	return PaymentResponse{
		TransactionID: txnID,
		Status:        "ok",
		Amount:        req.Amount,
	}, nil
}

// ============================================================
// SQL DDL for reference (what you'd run in production)
// ============================================================

func printDDL() {
	ddl := `
-- Pattern 1: Unique constraint on natural key
CREATE TABLE events (
    id          BIGSERIAL PRIMARY KEY,
    event_id    TEXT NOT NULL UNIQUE,          -- the dedup key
    user_id     TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    payload     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX events_event_id_idx ON events(event_id);

-- Insert with dedup (ignore duplicate)
INSERT INTO events (event_id, user_id, event_type, payload)
VALUES ($1, $2, $3, $4)
ON CONFLICT (event_id) DO NOTHING;

-- Insert with dedup (upsert — update if exists)
INSERT INTO events (event_id, user_id, event_type, payload)
VALUES ($1, $2, $3, $4)
ON CONFLICT (event_id) DO UPDATE
    SET payload    = EXCLUDED.payload,
        updated_at = NOW();

-- Pattern 2: Idempotency key table
CREATE TABLE idempotency_keys (
    key          TEXT PRIMARY KEY,
    status_code  INT,
    response     TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '24 hours'
);

-- Claim a key (returns nothing if already claimed)
INSERT INTO idempotency_keys (key)
VALUES ($1)
ON CONFLICT (key) DO NOTHING;

-- Store response
UPDATE idempotency_keys
SET status_code = $2, response = $3
WHERE key = $1;

-- Cleanup expired keys (run as a cron job)
DELETE FROM idempotency_keys WHERE expires_at < NOW();

-- Pattern 3: Composite unique key (dedup on multiple columns)
CREATE TABLE order_line_items (
    id          BIGSERIAL PRIMARY KEY,
    order_id    TEXT NOT NULL,
    product_id  TEXT NOT NULL,
    quantity    INT NOT NULL,
    UNIQUE (order_id, product_id)              -- composite dedup key
);

INSERT INTO order_line_items (order_id, product_id, quantity)
VALUES ($1, $2, $3)
ON CONFLICT (order_id, product_id) DO UPDATE
    SET quantity = order_line_items.quantity + EXCLUDED.quantity;
`
	fmt.Println(ddl)
}

// ============================================================
// Concurrent safety test
// ============================================================

func concurrentInsertTest(svc *EventService) {
	const eventID = "concurrent_event_999"
	var wg sync.WaitGroup
	wins := 0
	var mu sync.Mutex

	for i := 0; i < 5; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			before := svc.db.processedTotal
			svc.ProcessEvent(eventID, fmt.Sprintf("user_%d", id), "click", "payload")
			after := svc.db.processedTotal
			if after > before {
				mu.Lock()
				wins++
				mu.Unlock()
			}
		}(i)
	}
	wg.Wait()
	fmt.Printf("\n  %d/5 goroutines actually processed the event\n", wins)
}

func main() {
	db := NewMockDB()
	eventSvc := NewEventService(db)
	apiSvc := NewAPIService(db)

	fmt.Println("=== Pattern 1: ON CONFLICT DO NOTHING (event dedup) ===")
	events := []struct{ id, userID, typ, payload string }{
		{"evt_100", "user_1", "click", `{"element":"button"}`},
		{"evt_101", "user_2", "view", `{"page":"/home"}`},
		{"evt_100", "user_1", "click", `{"element":"button"}`}, // retry
		{"evt_102", "user_3", "signup", `{"plan":"pro"}`},
		{"evt_101", "user_2", "view", `{"page":"/home"}`},      // retry
		{"evt_100", "user_1", "click", `{"element":"button"}`}, // another retry
	}

	for _, e := range events {
		eventSvc.ProcessEvent(e.id, e.userID, e.typ, e.payload)
	}
	fmt.Printf("\nTotal processed: %d, Total conflicts skipped: %d\n",
		db.processedTotal, db.conflictTotal)

	fmt.Println("\n=== Pattern 2: Idempotency Keys (payment API) ===")
	apiSvc.CreatePayment(PaymentRequest{
		IdempotencyKey: "idem_abc123",
		Amount:         500.00,
		Currency:       "INR",
		RecipientID:    "vendor_42",
	})

	fmt.Println("Client retries (network timeout):")
	apiSvc.CreatePayment(PaymentRequest{
		IdempotencyKey: "idem_abc123", // same key
		Amount:         500.00,
		Currency:       "INR",
		RecipientID:    "vendor_42",
	})

	fmt.Println("Client retries again:")
	apiSvc.CreatePayment(PaymentRequest{
		IdempotencyKey: "idem_abc123",
		Amount:         500.00,
		Currency:       "INR",
		RecipientID:    "vendor_42",
	})

	fmt.Println("Different payment:")
	apiSvc.CreatePayment(PaymentRequest{
		IdempotencyKey: "idem_xyz999",
		Amount:         250.00,
		Currency:       "INR",
		RecipientID:    "vendor_7",
	})
	fmt.Printf("\nTotal payment executions: %d (expected: 2)\n", txnCounter)

	fmt.Println("\n=== Concurrent Insert Test ===")
	fmt.Println("5 goroutines racing to insert the same event_id:")
	concurrentInsertTest(eventSvc)

	fmt.Println("\n=== SQL DDL Reference ===")
	printDDL()
}
