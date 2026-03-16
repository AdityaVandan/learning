// Scale 6: MinHash + LSH (Locality Sensitive Hashing)
//
// Finds NEAR-DUPLICATES — documents that are similar but not identical.
// Used by: web crawlers (Common Crawl), plagiarism detectors, product catalog dedup.
//
// Pipeline:
//   1. Shingling:  Document → set of k-shingles (overlapping n-grams)
//   2. MinHash:    Shingle set → fixed-size signature (preserves Jaccard similarity)
//   3. LSH Banding: Signatures → hash buckets (similar sigs collide with high probability)
//   4. Candidates: Documents in the same bucket → compare directly
//
// Key insight: O(n²) pairwise comparison → O(n) with LSH
// Jaccard similarity: |A ∩ B| / |A ∪ B|

package main

import (
	"fmt"
	"hash/fnv"
	"math"
	"sort"
	"strings"
	"unicode"
)

// ============================================================
// Step 1: Shingling
// ============================================================

// Shingle creates overlapping k-character windows from text.
// "hello world" with k=3 → {"hel", "ell", "llo", "lo ", "o w", " wo", "wor", "orl", "rld"}
//
// Word-level shingles are more robust to minor edits than character-level.
func characterShingles(text string, k int) map[string]bool {
	text = normalizeText(text)
	shingles := make(map[string]bool)
	runes := []rune(text)
	for i := 0; i <= len(runes)-k; i++ {
		shingles[string(runes[i:i+k])] = true
	}
	return shingles
}

func wordShingles(text string, k int) map[string]bool {
	words := strings.Fields(normalizeText(text))
	shingles := make(map[string]bool)
	for i := 0; i <= len(words)-k; i++ {
		shingles[strings.Join(words[i:i+k], " ")] = true
	}
	return shingles
}

func normalizeText(text string) string {
	var sb strings.Builder
	for _, r := range strings.ToLower(text) {
		if unicode.IsLetter(r) || unicode.IsSpace(r) || unicode.IsDigit(r) {
			sb.WriteRune(r)
		}
	}
	return strings.Join(strings.Fields(sb.String()), " ")
}

// ============================================================
// Step 2: MinHash Signature
// ============================================================

// A MinHash signature approximates the Jaccard similarity between two sets.
// For numHashes hash functions h_1..h_n, the signature is:
//   sig[i] = min(h_i(x)) for all x in the shingle set
//
// The probability that sig_A[i] == sig_B[i] equals the Jaccard similarity.
// With 100+ hash functions, the estimate is very accurate.

type MinHasher struct {
	numHashes  int
	hashSeeds  []uint32 // one seed per hash function
}

func NewMinHasher(numHashes int) *MinHasher {
	seeds := make([]uint32, numHashes)
	// Use deterministic seeds derived from index
	for i := range seeds {
		h := fnv.New32a()
		h.Write([]byte(fmt.Sprintf("seed_%d", i)))
		seeds[i] = h.Sum32()
	}
	return &MinHasher{numHashes: numHashes, hashSeeds: seeds}
}

// hashWithSeed computes h(value, seed) using a simple universal hash:
// (a*x + b) mod p where p is a large prime
func (m *MinHasher) hashWithSeed(value string, seed uint32) uint32 {
	h := fnv.New32a()
	// Mix the seed into the hash
	buf := make([]byte, 4)
	buf[0] = byte(seed)
	buf[1] = byte(seed >> 8)
	buf[2] = byte(seed >> 16)
	buf[3] = byte(seed >> 24)
	h.Write(buf)
	h.Write([]byte(value))
	return h.Sum32()
}

// Signature computes the MinHash signature for a set of shingles.
func (m *MinHasher) Signature(shingles map[string]bool) []uint32 {
	sig := make([]uint32, m.numHashes)
	for i := range sig {
		sig[i] = math.MaxUint32 // start with ∞
	}

	for shingle := range shingles {
		for i, seed := range m.hashSeeds {
			h := m.hashWithSeed(shingle, seed)
			if h < sig[i] {
				sig[i] = h
			}
		}
	}
	return sig
}

// EstimatedJaccard estimates Jaccard similarity from two MinHash signatures.
func EstimatedJaccard(sigA, sigB []uint32) float64 {
	if len(sigA) != len(sigB) {
		return 0
	}
	matches := 0
	for i := range sigA {
		if sigA[i] == sigB[i] {
			matches++
		}
	}
	return float64(matches) / float64(len(sigA))
}

// ============================================================
// Step 3: LSH Banding
// ============================================================

// The banding technique amplifies the similarity signal.
// We split the signature into b bands of r rows each (numHashes = b * r).
// Two documents are candidate pairs if they match in at least one band.
//
// The probability of becoming a candidate pair is:
//   P(candidate) = 1 - (1 - s^r)^b
// where s is the true Jaccard similarity.
// This creates a steep S-curve: documents with s > threshold are very likely candidates,
// and documents with s < threshold are very unlikely candidates.

type LSHIndex struct {
	bands      int
	rows       int    // rows per band
	buckets    map[string][]string // band_hash → list of doc IDs
	signatures map[string][]uint32
}

func NewLSHIndex(bands, rows int) *LSHIndex {
	return &LSHIndex{
		bands:      bands,
		rows:       rows,
		buckets:    make(map[string][]string),
		signatures: make(map[string][]uint32),
	}
}

// Add inserts a document with its MinHash signature into the index.
func (idx *LSHIndex) Add(docID string, sig []uint32) {
	idx.signatures[docID] = sig

	for b := 0; b < idx.bands; b++ {
		start := b * idx.rows
		end := start + idx.rows
		if end > len(sig) {
			end = len(sig)
		}
		bandSig := sig[start:end]

		// Hash this band's values into a bucket key
		h := fnv.New64a()
		for _, v := range bandSig {
			buf := []byte{byte(v), byte(v >> 8), byte(v >> 16), byte(v >> 24)}
			h.Write(buf)
		}
		bucketKey := fmt.Sprintf("b%d_%d", b, h.Sum64())
		idx.buckets[bucketKey] = append(idx.buckets[bucketKey], docID)
	}
}

// CandidatePairs returns all pairs of documents that share at least one LSH bucket.
func (idx *LSHIndex) CandidatePairs() [][2]string {
	seen := make(map[string]bool)
	var pairs [][2]string

	for _, docs := range idx.buckets {
		if len(docs) < 2 {
			continue
		}
		// All pairs within this bucket
		for i := 0; i < len(docs); i++ {
			for j := i + 1; j < len(docs); j++ {
				a, b := docs[i], docs[j]
				if a > b {
					a, b = b, a
				}
				key := a + "|" + b
				if !seen[key] {
					seen[key] = true
					pairs = append(pairs, [2]string{a, b})
				}
			}
		}
	}
	return pairs
}

// Threshold returns the Jaccard similarity threshold for this configuration.
// Documents above this threshold will be found with high probability.
func (idx *LSHIndex) Threshold() float64 {
	// The S-curve inflection point (where P(candidate) ≈ 0.5) is at s = (1/b)^(1/r)
	return math.Pow(1.0/float64(idx.bands), 1.0/float64(idx.rows))
}

// ============================================================
// Full pipeline: deduplicate a document corpus
// ============================================================

type Document struct {
	ID   string
	Text string
}

type DedupResult struct {
	OriginalCount  int
	DuplicateGroups []DuplicateGroup
	UniqueDocIDs   []string
}

type DuplicateGroup struct {
	CanonicalID string
	DuplicateID string
	Similarity  float64
}

func DeduplicateCorpus(docs []Document, similarityThreshold float64) DedupResult {
	const numHashes = 100
	shingleSize := 3
	bands := 20
	rows := numHashes / bands

	hasher := NewMinHasher(numHashes)
	index := NewLSHIndex(bands, rows)

	// Step 1 & 2: Shingle + MinHash each document
	signatures := make(map[string][]uint32)
	for _, doc := range docs {
		shingles := wordShingles(doc.Text, shingleSize)
		if len(shingles) == 0 {
			shingles = characterShingles(doc.Text, shingleSize)
		}
		sig := hasher.Signature(shingles)
		signatures[doc.ID] = sig
		index.Add(doc.ID, sig)
	}

	// Step 3: Find candidate pairs from LSH
	candidates := index.CandidatePairs()

	// Step 4: Verify candidates with exact similarity computation
	var groups []DuplicateGroup
	duplicates := make(map[string]bool)

	// Sort candidates for deterministic output
	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i][0]+candidates[i][1] < candidates[j][0]+candidates[j][1]
	})

	for _, pair := range candidates {
		sim := EstimatedJaccard(signatures[pair[0]], signatures[pair[1]])
		if sim >= similarityThreshold {
			// The "earlier" doc is canonical; the "later" one is duplicate
			canonical, dup := pair[0], pair[1]
			if canonical > dup {
				canonical, dup = dup, canonical
			}
			groups = append(groups, DuplicateGroup{
				CanonicalID: canonical,
				DuplicateID: dup,
				Similarity:  sim,
			})
			duplicates[dup] = true
		}
	}

	// Build list of unique docs (not duplicates of anything)
	uniqueIDs := make([]string, 0)
	for _, doc := range docs {
		if !duplicates[doc.ID] {
			uniqueIDs = append(uniqueIDs, doc.ID)
		}
	}

	return DedupResult{
		OriginalCount:  len(docs),
		DuplicateGroups: groups,
		UniqueDocIDs:   uniqueIDs,
	}
}

// ============================================================
// Main
// ============================================================

func main() {
	fmt.Println("=== Step 1: Shingling Demo ===")
	text := "the quick brown fox jumps over the lazy dog"
	charShingles := characterShingles(text, 4)
	wordShingles3 := wordShingles(text, 3)
	fmt.Printf("Text: %q\n", text)
	fmt.Printf("Character shingles (k=4): %d shingles\n", len(charShingles))
	fmt.Printf("Word shingles (k=3): %d shingles\n", len(wordShingles3))
	i := 0
	fmt.Print("  Sample word shingles: ")
	for s := range wordShingles3 {
		fmt.Printf("%q ", s)
		if i++; i >= 4 {
			break
		}
	}
	fmt.Println("...")

	fmt.Println("\n=== Step 2: MinHash Jaccard Estimation ===")
	hasher := NewMinHasher(128)

	textA := "the quick brown fox jumps over the lazy dog"
	textB := "the quick brown fox leaps over the sleepy dog" // slightly different
	textC := "lorem ipsum dolor sit amet consectetur adipiscing elit"

	shinglesA := wordShingles(textA, 2)
	shinglesB := wordShingles(textB, 2)
	shinglesC := wordShingles(textC, 2)

	sigA := hasher.Signature(shinglesA)
	sigB := hasher.Signature(shinglesB)
	sigC := hasher.Signature(shinglesC)

	// True Jaccard
	trueJaccard := func(a, b map[string]bool) float64 {
		inter, union := 0, 0
		for k := range a {
			if b[k] {
				inter++
			}
		}
		for range a {
			union++
		}
		for k := range b {
			if !a[k] {
				union++
			}
		}
		return float64(inter) / float64(union)
	}

	fmt.Printf("Text A vs B (similar):\n")
	fmt.Printf("  True Jaccard:      %.3f\n", trueJaccard(shinglesA, shinglesB))
	fmt.Printf("  MinHash estimated: %.3f\n", EstimatedJaccard(sigA, sigB))

	fmt.Printf("Text A vs C (dissimilar):\n")
	fmt.Printf("  True Jaccard:      %.3f\n", trueJaccard(shinglesA, shinglesC))
	fmt.Printf("  MinHash estimated: %.3f\n", EstimatedJaccard(sigA, sigC))

	fmt.Println("\n=== Step 3: LSH Banding — Threshold Analysis ===")
	configs := []struct{ bands, rows int }{
		{10, 10},
		{20, 5},
		{50, 2},
		{25, 4},
	}
	fmt.Printf("%-10s %-8s %-8s %s\n", "Bands", "Rows", "Hashes", "Threshold (~)")
	for _, c := range configs {
		idx := NewLSHIndex(c.bands, c.rows)
		fmt.Printf("%-10d %-8d %-8d %.3f\n", c.bands, c.rows, c.bands*c.rows, idx.Threshold())
	}

	fmt.Println("\n=== Full Deduplication Pipeline ===")
	docs := []Document{
		{
			ID:   "doc_1",
			Text: "Scientists discover new species of deep sea fish near the Mariana Trench",
		},
		{
			ID:   "doc_2",
			Text: "Researchers find new species of deep sea fish near the Mariana Trench",
		},
		{
			ID:   "doc_3",
			Text: "Go programming language sees major performance improvements in version 1.22",
		},
		{
			ID:   "doc_4",
			Text: "Scientists discover new species of deep sea fish near the Mariana Trench exploration",
		},
		{
			ID:   "doc_5",
			Text: "The Golang programming language gets significant performance boosts in release 1.22",
		},
		{
			ID:   "doc_6",
			Text: "The stock market closed higher today driven by technology sector gains",
		},
		{
			ID:   "doc_7",
			Text: "Stock markets ended the day higher fueled by gains in the technology sector",
		},
		{
			ID:   "doc_8",
			Text: "Completely unrelated article about ancient Roman architecture and its influence",
		},
	}

	fmt.Printf("Corpus: %d documents\n", len(docs))
	fmt.Println("Running MinHash + LSH deduplication (threshold: 0.5)...")
	result := DeduplicateCorpus(docs, 0.5)

	fmt.Printf("\nDuplicate groups found: %d\n", len(result.DuplicateGroups))
	for _, g := range result.DuplicateGroups {
		fmt.Printf("  [SIMILAR %.2f] %s ≈ %s\n", g.Similarity, g.CanonicalID, g.DuplicateID)

		// Show the actual texts
		for _, doc := range docs {
			if doc.ID == g.CanonicalID {
				fmt.Printf("    canonical: %q\n", doc.Text[:min(60, len(doc.Text))]+"...")
			}
			if doc.ID == g.DuplicateID {
				fmt.Printf("    duplicate: %q\n", doc.Text[:min(60, len(doc.Text))]+"...")
			}
		}
	}

	fmt.Printf("\nUnique documents after dedup: %d/%d\n", len(result.UniqueDocIDs), result.OriginalCount)
	fmt.Printf("Unique doc IDs: %v\n", result.UniqueDocIDs)

	fmt.Println("\n=== Scalability Analysis ===")
	fmt.Println("Pairwise comparison complexity:")
	sizes := []int{1_000, 10_000, 100_000, 1_000_000}
	for _, n := range sizes {
		pairwise := int64(n) * int64(n-1) / 2
		lsh := int64(n) * 100 // ~100 hash ops per doc + sparse candidate pairs
		fmt.Printf("  n=%10s  brute force: %15d comparisons  LSH: ~%10d ops\n",
			formatInt(n), pairwise, lsh)
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
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
