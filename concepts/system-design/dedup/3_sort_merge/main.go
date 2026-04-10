// Scale 3: Sort-Merge Deduplication
//
// For datasets larger than RAM: sort the data so duplicates become adjacent,
// then do a single linear scan to eliminate them.
//
// This is the core pattern in:
//   - ETL pipelines (dedup before loading to warehouse)
//   - External sort-based dedup in databases
//   - Hadoop MapReduce (shuffle phase sorts keys, reducer deduplicates)
//
// Memory: O(chunk_size) — only one chunk in RAM at a time
// Time:   O(n log n) for sort + O(n) for merge scan

package main

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"
)

type Record struct {
	ID        string
	Name      string
	Email     string
	Timestamp int64
}

func (r Record) dedupeKey() string {
	return r.ID
}

// --- In-memory sort-merge (for datasets that fit in RAM) ---

func sortMergeDedup(records []Record) []Record {
	// Step 1: Sort by dedup key
	sort.Slice(records, func(i, j int) bool {
		return records[i].dedupeKey() < records[j].dedupeKey()
	})

	// Step 2: Single linear scan — keep first occurrence of each key
	result := make([]Record, 0, len(records))
	for i, r := range records {
		if i == 0 || r.dedupeKey() != records[i-1].dedupeKey() {
			result = append(result, r)
		}
	}
	return result
}

// sortMergeDedupLastWins: keep the record with the highest Timestamp
// This is useful when you have updates and want the most current record.
func sortMergeDedupLastWins(records []Record) []Record {
	// Sort by (key ASC, timestamp DESC) so the most recent comes first per key
	sort.Slice(records, func(i, j int) bool {
		if records[i].dedupeKey() != records[j].dedupeKey() {
			return records[i].dedupeKey() < records[j].dedupeKey()
		}
		return records[i].Timestamp > records[j].Timestamp // newer first
	})

	result := make([]Record, 0, len(records))
	for i, r := range records {
		if i == 0 || r.dedupeKey() != records[i-1].dedupeKey() {
			result = append(result, r) // always the most recent version
		}
	}
	return result
}

// --- External Sort-Merge Dedup (for datasets larger than RAM) ---
//
// Step 1: Read the file in chunks, sort each chunk, write to temp files (run files)
// Step 2: k-way merge the sorted run files, emitting only unique records
//
// This is a simplified version — real implementations use memory-mapped files
// and priority queues for the merge phase.

const chunkSize = 5 // small for demo; in production this would be millions

func writeChunkToFile(chunk []Record, filename string) error {
	f, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer f.Close()

	w := csv.NewWriter(f)
	for _, r := range chunk {
		w.Write([]string{r.ID, r.Name, r.Email, strconv.FormatInt(r.Timestamp, 10)})
	}
	w.Flush()
	return w.Error()
}

func readAllFromFile(filename string) ([]Record, error) {
	f, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	rows, err := r.ReadAll()
	if err != nil {
		return nil, err
	}

	records := make([]Record, 0, len(rows))
	for _, row := range rows {
		ts, _ := strconv.ParseInt(row[3], 10, 64)
		records = append(records, Record{
			ID:        row[0],
			Name:      row[1],
			Email:     row[2],
			Timestamp: ts,
		})
	}
	return records, nil
}

// externalSortMergeDedup processes a large "file" (simulated as a slice here)
// by splitting it into sorted chunks and then merging them.
func externalSortMergeDedup(allRecords []Record, tmpDir string) ([]Record, error) {
	// --- Phase 1: Create sorted run files ---
	runFiles := []string{}
	for i := 0; i < len(allRecords); i += chunkSize {
		end := i + chunkSize
		if end > len(allRecords) {
			end = len(allRecords)
		}
		chunk := make([]Record, end-i)
		copy(chunk, allRecords[i:end])

		// Sort this chunk
		sort.Slice(chunk, func(a, b int) bool {
			if chunk[a].dedupeKey() != chunk[b].dedupeKey() {
				return chunk[a].dedupeKey() < chunk[b].dedupeKey()
			}
			return chunk[a].Timestamp > chunk[b].Timestamp
		})

		filename := fmt.Sprintf("%s/run_%d.csv", tmpDir, len(runFiles))
		if err := writeChunkToFile(chunk, filename); err != nil {
			return nil, err
		}
		runFiles = append(runFiles, filename)
		fmt.Printf("  Created run file: %s (%d records)\n", filename, len(chunk))
	}

	// --- Phase 2: k-way merge ---
	// Load all run files into memory for this demo.
	// In production: use a min-heap with one record per run file for O(n log k) merge.
	fmt.Printf("\n  Merging %d run files...\n", len(runFiles))

	allSorted := []Record{}
	for _, f := range runFiles {
		records, err := readAllFromFile(f)
		if err != nil {
			return nil, err
		}
		allSorted = append(allSorted, records...)
		os.Remove(f)
	}

	// Final sort of merged data (in production the merge preserves order via heap)
	sort.Slice(allSorted, func(i, j int) bool {
		if allSorted[i].dedupeKey() != allSorted[j].dedupeKey() {
			return allSorted[i].dedupeKey() < allSorted[j].dedupeKey()
		}
		return allSorted[i].Timestamp > allSorted[j].Timestamp
	})

	// Dedup scan — keep first of each key (which is the most recent due to sort order)
	result := make([]Record, 0)
	for i, r := range allSorted {
		if i == 0 || r.dedupeKey() != allSorted[i-1].dedupeKey() {
			result = append(result, r)
		}
	}

	return result, nil
}

// --- CSV file dedup (real-world use case) ---

func dedupCSVFile(inputPath, outputPath, keyColumn string) error {
	in, err := os.Open(inputPath)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(outputPath)
	if err != nil {
		return err
	}
	defer out.Close()

	reader := csv.NewReader(bufio.NewReader(in))
	writer := csv.NewWriter(bufio.NewWriter(out))
	defer writer.Flush()

	// Read header
	header, err := reader.Read()
	if err != nil {
		return err
	}
	writer.Write(header)

	// Find key column index
	keyIdx := -1
	for i, col := range header {
		if col == keyColumn {
			keyIdx = i
			break
		}
	}
	if keyIdx == -1 {
		return fmt.Errorf("key column %q not found in header", keyColumn)
	}

	// Read all rows, build (key → row) map, then write unique rows
	// For truly large files, you'd sort first then scan
	seen := make(map[string][]string)
	var orderedKeys []string

	for {
		row, err := reader.Read()
		if err != nil {
			break
		}
		key := row[keyIdx]
		if _, exists := seen[key]; !exists {
			seen[key] = row
			orderedKeys = append(orderedKeys, key)
		}
	}

	for _, key := range orderedKeys {
		writer.Write(seen[key])
	}

	return nil
}

func generateTestCSV(path string) {
	f, _ := os.Create(path)
	defer f.Close()
	w := csv.NewWriter(f)
	w.Write([]string{"id", "name", "email"})
	rows := [][]string{
		{"1", "Alice", "alice@example.com"},
		{"2", "Bob", "bob@example.com"},
		{"1", "Alice", "alice@example.com"},  // duplicate
		{"3", "Carol", "carol@example.com"},
		{"2", "Bob", "bob@example.com"},      // duplicate
		{"4", "Dave", "dave@example.com"},
	}
	for _, r := range rows {
		w.Write(r)
	}
	w.Flush()
}

func main() {
	fmt.Println("=== In-Memory Sort-Merge Dedup ===")
	records := []Record{
		{ID: "id_003", Name: "Carol", Email: "carol@x.com", Timestamp: 1000},
		{ID: "id_001", Name: "Alice", Email: "alice@old.com", Timestamp: 500},
		{ID: "id_002", Name: "Bob", Email: "bob@x.com", Timestamp: 2000},
		{ID: "id_001", Name: "Alice", Email: "alice@new.com", Timestamp: 3000}, // newer duplicate
		{ID: "id_003", Name: "Carol", Email: "carol@x.com", Timestamp: 1500},  // duplicate
		{ID: "id_004", Name: "Dave", Email: "dave@x.com", Timestamp: 4000},
		{ID: "id_002", Name: "Bob", Email: "bob@x.com", Timestamp: 1000},      // older duplicate
	}

	fmt.Printf("Input records: %d\n\n", len(records))

	firstWins := sortMergeDedup(records)
	fmt.Println("First-wins strategy (keeps earliest seen):")
	for _, r := range firstWins {
		fmt.Printf("  %s | %s | ts=%d\n", r.ID, r.Email, r.Timestamp)
	}

	lastWins := sortMergeDedupLastWins(records)
	fmt.Println("\nLast-wins strategy (keeps most recent by timestamp):")
	for _, r := range lastWins {
		fmt.Printf("  %s | %s | ts=%d\n", r.ID, r.Email, r.Timestamp)
	}

	fmt.Printf("\nDedup reduced %d → %d records\n", len(records), len(lastWins))

	fmt.Println("\n=== External Sort-Merge Dedup (simulated) ===")
	tmpDir := "/tmp/dedup_sort_merge"
	os.MkdirAll(tmpDir, 0755)

	// Generate a larger dataset
	bigData := make([]Record, 0, 20)
	names := []string{"Alice", "Bob", "Carol", "Dave", "Eve"}
	for i := 0; i < 20; i++ {
		id := fmt.Sprintf("id_%03d", (i%7)+1) // 7 unique IDs → lots of duplicates
		bigData = append(bigData, Record{
			ID:        id,
			Name:      names[i%len(names)],
			Email:     fmt.Sprintf("%s@example.com", strings.ToLower(names[i%len(names)])),
			Timestamp: int64(i * 100),
		})
	}

	fmt.Printf("Input: %d records, %d unique IDs expected\n\n", len(bigData), 7)
	result, err := externalSortMergeDedup(bigData, tmpDir)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	fmt.Printf("\nResult: %d unique records\n", len(result))
	for _, r := range result {
		fmt.Printf("  %s | %s | ts=%d (most recent kept)\n", r.ID, r.Name, r.Timestamp)
	}

	fmt.Println("\n=== CSV File Deduplication ===")
	inputCSV := "/tmp/test_dedup_input.csv"
	outputCSV := "/tmp/test_dedup_output.csv"
	generateTestCSV(inputCSV)

	if err := dedupCSVFile(inputCSV, outputCSV, "id"); err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	// Print output
	f, _ := os.Open(outputCSV)
	scanner := bufio.NewScanner(f)
	fmt.Println("Deduplicated CSV output:")
	for scanner.Scan() {
		fmt.Printf("  %s\n", scanner.Text())
	}
	f.Close()

	os.RemoveAll(tmpDir)
	os.Remove(inputCSV)
	os.Remove(outputCSV)
}
