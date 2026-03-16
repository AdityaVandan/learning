// Scale 2: Bloom Filter Deduplication
//
// A Bloom filter is a probabilistic data structure that answers membership
// queries with "definitely not seen" or "probably seen". It never has false
// negatives but can have false positives (configurable rate).
//
// Tradeoff vs hash set:
//   Hash set:    100% accurate, ~50 bytes/item
//   Bloom filter: ~1% FP rate, ~1 byte/item (50x more space-efficient)
//
// Best for: high-volume dedup where occasional false positives are acceptable
//           (e.g., skipping a network fetch, not financial transactions)

package main

import (
	"encoding/binary"
	"fmt"
	"hash/fnv"
	"math"
)

// BloomFilter is a space-efficient probabilistic set.
type BloomFilter struct {
	bits     []uint64 // bit array stored as uint64 words
	numBits  uint     // total number of bits (m)
	numHash  uint     // number of hash functions (k)
	count    uint     // number of items added (for FP rate estimation)
}

// NewBloomFilter creates a filter tuned for n expected items and target false-positive rate p.
// It calculates optimal m (bit count) and k (hash function count).
//
// Formulas:
//   m = -n*ln(p) / (ln(2)^2)
//   k = (m/n) * ln(2)
func NewBloomFilter(n uint, p float64) *BloomFilter {
	m := uint(math.Ceil(-float64(n) * math.Log(p) / (math.Ln2 * math.Ln2)))
	k := uint(math.Ceil((float64(m) / float64(n)) * math.Ln2))

	// Round m up to next multiple of 64 for clean uint64 storage
	words := (m + 63) / 64
	m = words * 64

	return &BloomFilter{
		bits:    make([]uint64, words),
		numBits: m,
		numHash: k,
	}
}

// hashes generates k independent hash values for the given key using
// the "double hashing" technique: h_i(x) = h1(x) + i*h2(x)
// This avoids needing k independent hash functions.
func (bf *BloomFilter) hashes(key []byte) []uint {
	h1 := fnv.New64()
	h1.Write(key)
	v1 := h1.Sum64()

	h2 := fnv.New64a()
	h2.Write(key)
	v2 := h2.Sum64()

	positions := make([]uint, bf.numHash)
	for i := uint(0); i < bf.numHash; i++ {
		positions[i] = uint((v1 + uint64(i)*v2) % uint64(bf.numBits))
	}
	return positions
}

func (bf *BloomFilter) setBit(pos uint) {
	bf.bits[pos/64] |= 1 << (pos % 64)
}

func (bf *BloomFilter) getBit(pos uint) bool {
	return bf.bits[pos/64]&(1<<(pos%64)) != 0
}

// Add inserts an item into the filter.
func (bf *BloomFilter) Add(key []byte) {
	for _, pos := range bf.hashes(key) {
		bf.setBit(pos)
	}
	bf.count++
}

// Contains checks if an item is probably in the filter.
// Returns false  → definitely not seen (no false negatives)
// Returns true   → probably seen (small chance of false positive)
func (bf *BloomFilter) Contains(key []byte) bool {
	for _, pos := range bf.hashes(key) {
		if !bf.getBit(pos) {
			return false
		}
	}
	return true
}

// FalsePositiveRate estimates the current FP rate based on items added.
// Formula: (1 - e^(-k*n/m))^k
func (bf *BloomFilter) FalsePositiveRate() float64 {
	exponent := -float64(bf.numHash) * float64(bf.count) / float64(bf.numBits)
	return math.Pow(1-math.Exp(exponent), float64(bf.numHash))
}

// SizeBytes returns memory used by the bit array.
func (bf *BloomFilter) SizeBytes() int {
	return len(bf.bits) * 8
}

// Stats prints configuration and current state.
func (bf *BloomFilter) Stats() {
	fmt.Printf("  Bit array size:    %d bits (%.2f KB)\n", bf.numBits, float64(bf.numBits)/8/1024)
	fmt.Printf("  Hash functions:    %d\n", bf.numHash)
	fmt.Printf("  Items added:       %d\n", bf.count)
	fmt.Printf("  Est. FP rate:      %.4f%%\n", bf.FalsePositiveRate()*100)
}

// --- Scalable Bloom Filter ---
// A standard Bloom filter has a fixed capacity. When it fills up, the FP rate
// degrades. A Scalable Bloom Filter grows by adding new layers when needed.

type ScalableBloomFilter struct {
	filters    []*BloomFilter
	targetFP   float64
	initN      uint
	fpTightening float64 // each new layer has tighter FP target
}

func NewScalableBloomFilter(initialN uint, targetFP float64) *ScalableBloomFilter {
	sbf := &ScalableBloomFilter{
		targetFP:     targetFP,
		initN:        initialN,
		fpTightening: 0.9, // each new filter uses 90% of the previous FP budget
	}
	sbf.addLayer()
	return sbf
}

func (sbf *ScalableBloomFilter) currentFP() float64 {
	return sbf.targetFP * math.Pow(sbf.fpTightening, float64(len(sbf.filters)))
}

func (sbf *ScalableBloomFilter) addLayer() {
	n := sbf.initN * uint(math.Pow(2, float64(len(sbf.filters)))) // double capacity each time
	fp := sbf.currentFP()
	sbf.filters = append(sbf.filters, NewBloomFilter(n, fp))
}

func (sbf *ScalableBloomFilter) Add(key []byte) {
	currentFilter := sbf.filters[len(sbf.filters)-1]
	// If current layer is at ~80% capacity (FP rate has degraded), add new layer
	if currentFilter.FalsePositiveRate() > sbf.targetFP*1.1 {
		sbf.addLayer()
		currentFilter = sbf.filters[len(sbf.filters)-1]
	}
	currentFilter.Add(key)
}

func (sbf *ScalableBloomFilter) Contains(key []byte) bool {
	// Check all layers — item could be in any of them
	for _, f := range sbf.filters {
		if f.Contains(key) {
			return true
		}
	}
	return false
}

// --- Deduplication pipeline using Bloom filter ---

type Message struct {
	ID   string
	Body string
}

func dedupWithBloom(messages []Message, bf *BloomFilter) (processed, skipped int) {
	for _, m := range messages {
		key := []byte(m.ID)
		if bf.Contains(key) {
			skipped++
			continue
		}
		bf.Add(key)
		processed++
		// process(m) ...
	}
	return
}

func main() {
	fmt.Println("=== Bloom Filter Configuration ===")
	// Tuned for 1 million items with 0.1% false positive rate
	bf := NewBloomFilter(1_000_000, 0.001)
	fmt.Printf("For n=1,000,000 items at 0.1%% FP rate:\n")
	bf.Stats()
	fmt.Println()

	// Compare to hash map memory
	hashMapBytes := 1_000_000 * 50 // ~50 bytes per map entry
	fmt.Printf("  Hash map would need: ~%d KB\n", hashMapBytes/1024)
	fmt.Printf("  Bloom filter needs:  ~%d KB (%.1fx savings)\n",
		bf.SizeBytes()/1024,
		float64(hashMapBytes)/float64(bf.SizeBytes()))

	fmt.Println("\n=== Deduplication Demo ===")
	messages := []Message{
		{ID: "msg_001", Body: "Hello"},
		{ID: "msg_002", Body: "World"},
		{ID: "msg_001", Body: "Hello"},    // duplicate
		{ID: "msg_003", Body: "!"},
		{ID: "msg_002", Body: "World"},    // duplicate
		{ID: "msg_004", Body: "New"},
	}

	bf2 := NewBloomFilter(1000, 0.01)
	processed, skipped := dedupWithBloom(messages, bf2)
	fmt.Printf("Processed: %d, Skipped (duplicates): %d\n", processed, skipped)

	fmt.Println("\n=== False Positive Rate Verification ===")
	testBF := NewBloomFilter(100, 0.01)

	// Add 100 items
	added := make(map[string]bool)
	for i := 0; i < 100; i++ {
		key := []byte(fmt.Sprintf("item_%d", i))
		testBF.Add(key)
		added[fmt.Sprintf("item_%d", i)] = true
	}

	// Test 10,000 unseen items — count false positives
	fpCount := 0
	testCount := 10_000
	for i := 10000; i < 10000+testCount; i++ {
		key := []byte(fmt.Sprintf("item_%d", i))
		if testBF.Contains(key) {
			fpCount++ // this is a false positive (we never added these)
		}
	}
	fmt.Printf("Expected FP rate: ~1.00%%\n")
	fmt.Printf("Observed FP rate: %.2f%% (%d/%d)\n",
		float64(fpCount)/float64(testCount)*100, fpCount, testCount)
	testBF.Stats()

	fmt.Println("\n=== Scalable Bloom Filter ===")
	sbf := NewScalableBloomFilter(100, 0.01)
	// Add 500 items (5x the initial capacity)
	for i := 0; i < 500; i++ {
		key := []byte(fmt.Sprintf("scalable_item_%d", i))
		sbf.Add(key)
	}
	fmt.Printf("Added 500 items to a filter with initial capacity 100\n")
	fmt.Printf("Layers created: %d\n", len(sbf.filters))
	fmt.Printf("All items still found: %v\n", func() bool {
		for i := 0; i < 500; i++ {
			if !sbf.Contains([]byte(fmt.Sprintf("scalable_item_%d", i))) {
				return false
			}
		}
		return true
	}())

	// Show bit array serialization (for persistence)
	fmt.Println("\n=== Serialization (for persistence) ===")
	bf3 := NewBloomFilter(1000, 0.01)
	bf3.Add([]byte("persist_me"))

	buf := make([]byte, len(bf3.bits)*8)
	for i, word := range bf3.bits {
		binary.LittleEndian.PutUint64(buf[i*8:], word)
	}
	fmt.Printf("Serialized %d bits to %d bytes\n", bf3.numBits, len(buf))

	// Restore
	bf4 := &BloomFilter{
		bits:    make([]uint64, len(bf3.bits)),
		numBits: bf3.numBits,
		numHash: bf3.numHash,
	}
	for i := range bf4.bits {
		bf4.bits[i] = binary.LittleEndian.Uint64(buf[i*8:])
	}
	fmt.Printf("Restored filter — 'persist_me' found: %v\n", bf4.Contains([]byte("persist_me")))
	fmt.Printf("Restored filter — 'never_added' found: %v\n", bf4.Contains([]byte("never_added")))
}
