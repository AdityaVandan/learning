// Scale 1: In-Memory Deduplication using Hash Sets
// Best for: datasets that fit in RAM, exact deduplication
// Time:  O(n) average | Space: O(unique items)
package main

import (
	"crypto/sha256"
	"fmt"
	"strings"
)

// --- Approach A: Dedup by explicit ID field ---

type Event struct {
	ID      string
	Payload string
}

func dedupByID(events []Event) []Event {
	seen := make(map[string]struct{}, len(events))
	result := make([]Event, 0, len(events))

	for _, e := range events {
		if _, exists := seen[e.ID]; exists {
			continue
		}
		seen[e.ID] = struct{}{}
		result = append(result, e)
	}
	return result
}

// --- Approach B: Dedup by content hash (no explicit ID) ---
// Useful when records don't have natural keys — hash the entire content.

func contentHash(fields ...string) string {
	h := sha256.New()
	for _, f := range fields {
		h.Write([]byte(f))
		h.Write([]byte{0}) // null separator to avoid "ab"+"c" == "a"+"bc"
	}
	return fmt.Sprintf("%x", h.Sum(nil))
}

type Product struct {
	Name     string
	SKU      string
	Category string
	Price    float64
}

func dedupProducts(products []Product) []Product {
	seen := make(map[string]struct{})
	result := make([]Product, 0)

	for _, p := range products {
		key := contentHash(
			p.Name,
			p.SKU,
			p.Category,
			fmt.Sprintf("%.4f", p.Price),
		)
		if _, exists := seen[key]; exists {
			continue
		}
		seen[key] = struct{}{}
		result = append(result, p)
	}
	return result
}

// --- Approach C: Dedup with "last write wins" merge strategy ---
// Instead of dropping duplicates, merge them: keep the most recently seen version.

type UserRecord struct {
	ID        string
	Name      string
	Email     string
	UpdatedAt int64 // unix timestamp
}

func dedupUsersLastWriteWins(records []UserRecord) []UserRecord {
	latest := make(map[string]UserRecord)

	for _, r := range records {
		existing, exists := latest[r.ID]
		if !exists || r.UpdatedAt > existing.UpdatedAt {
			latest[r.ID] = r
		}
	}

	result := make([]UserRecord, 0, len(latest))
	for _, r := range latest {
		result = append(result, r)
	}
	return result
}

// --- Approach D: Streaming dedup with a channel pipeline ---
// Useful when you're processing records as they arrive, not in a batch.

func dedupStream(input <-chan Event) <-chan Event {
	output := make(chan Event)

	go func() {
		defer close(output)
		seen := make(map[string]struct{})
		for e := range input {
			if _, exists := seen[e.ID]; !exists {
				seen[e.ID] = struct{}{}
				output <- e
			}
		}
	}()

	return output
}

func main() {
	fmt.Println("=== Approach A: Dedup by ID ===")
	events := []Event{
		{ID: "evt_1", Payload: "login"},
		{ID: "evt_2", Payload: "purchase"},
		{ID: "evt_1", Payload: "login"},  // duplicate
		{ID: "evt_3", Payload: "logout"},
		{ID: "evt_2", Payload: "purchase"}, // duplicate
	}
	deduped := dedupByID(events)
	fmt.Printf("Input: %d events → Output: %d unique events\n", len(events), len(deduped))
	for _, e := range deduped {
		fmt.Printf("  %s: %s\n", e.ID, e.Payload)
	}

	fmt.Println("\n=== Approach B: Dedup by Content Hash ===")
	products := []Product{
		{Name: "Widget A", SKU: "W-001", Category: "Tools", Price: 9.99},
		{Name: "Widget B", SKU: "W-002", Category: "Tools", Price: 14.99},
		{Name: "Widget A", SKU: "W-001", Category: "Tools", Price: 9.99}, // exact duplicate
		{Name: "Widget A", SKU: "W-001", Category: "Tools", Price: 10.99}, // different price → NOT a duplicate
	}
	dedupedProducts := dedupProducts(products)
	fmt.Printf("Input: %d products → Output: %d unique products\n", len(products), len(dedupedProducts))
	for _, p := range dedupedProducts {
		fmt.Printf("  SKU=%s Name=%s Price=%.2f\n", p.SKU, p.Name, p.Price)
	}

	fmt.Println("\n=== Approach C: Last Write Wins Merge ===")
	users := []UserRecord{
		{ID: "u1", Name: "Alice", Email: "alice@old.com", UpdatedAt: 1000},
		{ID: "u2", Name: "Bob", Email: "bob@example.com", UpdatedAt: 2000},
		{ID: "u1", Name: "Alice", Email: "alice@new.com", UpdatedAt: 3000}, // newer update
		{ID: "u1", Name: "Alice", Email: "alice@stale.com", UpdatedAt: 500}, // older — should be ignored
	}
	dedupedUsers := dedupUsersLastWriteWins(users)
	fmt.Printf("Input: %d records → Output: %d unique users\n", len(users), len(dedupedUsers))
	for _, u := range dedupedUsers {
		fmt.Printf("  %s: %s (%s)\n", u.ID, u.Name, u.Email)
	}

	fmt.Println("\n=== Approach D: Streaming Pipeline Dedup ===")
	input := make(chan Event, 10)
	streamEvents := []Event{
		{ID: "s1", Payload: "click"},
		{ID: "s2", Payload: "view"},
		{ID: "s1", Payload: "click"},
		{ID: "s3", Payload: "scroll"},
	}
	for _, e := range streamEvents {
		input <- e
	}
	close(input)

	output := dedupStream(input)
	count := 0
	for e := range output {
		fmt.Printf("  Processed: %s\n", e.ID)
		count++
	}
	fmt.Printf("  %d/%d events passed through\n", count, len(streamEvents))

	// Show memory cost of the seen map
	fmt.Println("\n=== Memory Analysis ===")
	n := 1_000_000
	// Each map entry in Go: ~8 bytes key pointer + 8 bytes value + ~8 bytes overhead ≈ ~50 bytes per entry
	estimatedMB := float64(n) * 50 / (1024 * 1024)
	fmt.Printf("Estimated memory for %s unique string keys: ~%.1f MB\n",
		formatInt(n), estimatedMB)
	fmt.Printf("At 100M unique items: ~%.1f GB — beyond this, use a Bloom filter\n",
		float64(n)*100*50/(1024*1024*1024))
	_ = strings.Contains // suppress import warning
}

func formatInt(n int) string {
	s := fmt.Sprintf("%d", n)
	result := ""
	for i, c := range s {
		if i > 0 && (len(s)-i)%3 == 0 {
			result += ","
		}
		result += string(c)
	}
	return result
}
