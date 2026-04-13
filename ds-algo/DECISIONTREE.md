# DS & Algo problem-solving decision tree

Use this as a **pattern router**, not a rigid script. Most problems mix patterns; start from **constraints** and **what you must optimize**, then narrow candidates.

---

## 1. First pass: lock the problem shape

Answer these before picking an algorithm family.

```mermaid
flowchart TD
  A[Read statement + examples] --> B{Exact output type?}
  B -->|Yes/No/Count/Path/Structure| C[Write invariants + edge cases]
  C --> D{Constraints: n, value range, updates?}
  D --> E[Target time / space budget]
  E --> F{Can brute force inform the structure?}
  F -->|Small n only| G[Brute / enumerate to see pattern]
  F -->|Large n| H[Jump to pattern tree below]
  G --> H
```

**Quick constraint cheat sheet**

| Typical `n` | Roughly feasible |
|-------------|------------------|
| ≤ 10–12 | Factorial / permutations, bitmask over subsets |
| ≤ 20–22 | `O(2^n)` with pruning |
| ≤ 10² | `O(n³)` sometimes |
| ≤ 10³–10⁴ | `O(n²)` or `O(n log n)` |
| ≤ 10⁵–10⁶ | `O(n)` or `O(n log n)` |
| ≥ 10⁶ | Usually `O(n)` or near-linear; heavy preprocessing only if queries amortize |

---

## 2. Master pattern router (high level)

```mermaid
flowchart TD
  START[What is the core object?] --> SEQ[Sequence: array / string]
  START --> GRAPH[Graph / grid / relationships]
  START --> TREE[Tree / hierarchy]
  START --> STRUCT[Design: LRU / iterator / rate limiter]
  START --> MATH[Pure math / combinatorics / bits]

  SEQ --> S1[See Section 3: Arrays & strings]
  GRAPH --> G1[See Section 4: Graphs & grids]
  TREE --> T1[See Section 5: Trees]
  STRUCT --> D1[See Section 10: Data structure design]
  MATH --> M1[See Section 9: Math & bits]
```

---

## 3. Arrays, strings, and substructures

```mermaid
flowchart TD
  A[Array / string problem] --> B{Need all pairs / subarrays with a property?}

  B -->|Subarray / substring contiguous| C{Fixed length?}
  C -->|Yes| SWF[Sliding window fixed]
  C -->|No| SWV[Sliding window variable + shrink]
  C -->|Max sum subarray| KAD[Kadane]

  B -->|Two ends symmetric| TP[Two pointers from both ends]
  B -->|Partition by condition| TP2[Two pointers same direction / Dutch flag]

  B -->|Prefix / range sum| PS[Prefix sums + hash map for complements]
  B -->|Many range queries| ST[Prefix + diff array / Fenwick / segment tree]

  B -->|Order statistics / k-th| HEAP[Heap quickselect]
  B -->|Sorted / monotonic property| MS[Monotonic stack or deque]

  B -->|Intervals overlap| MI[Sort by start + merge or sweep line]
  B -->|Cyclic array / index mapping| IDX[Index as key / cyclic sort]

  B -->|String: repeat / match| STR[KMP / rolling hash / Z-fn when needed]

  SWF --> NOTE[Window invariant is the key]
  SWV --> NOTE
```

**Pattern notes (when to reach)**

- **Sliding window**: contiguous segment, optimize sum/count/distinctness with `O(n)`.
- **Two pointers**: sorted data, palindrome-like, pair with target, partition in one pass.
- **Prefix sum + map**: subarray sum = `k`, count of sums divisible by `k`, “number of …”.
- **Monotonic stack**: next greater/smaller, histogram largest rectangle, trap rain water.
- **Monotonic deque**: sliding window min/max.
- **Binary search on answer**: “minimize maximum”, “maximize minimum”, feasibility check monotonic.

---

## 4. Graphs, grids, and connectivity

```mermaid
flowchart TD
  G[Graph / grid] --> W{Weighted?}
  W -->|No / unit weight| BFS[BFS: shortest layers, 01-BFS if 0/1 edges]
  W -->|Non-negative weights| DIJ[Dijkstra + heap]
  W -->|Negative edges| BF[Bellman-Ford / SPFA with care]

  G --> CYC{Cycle?}
  CYC -->|Undirected| UF[Union-Find or DFS colors]
  CYC -->|Directed| TOPO[Topo fails = cycle OR Tarjan/Kosaraju for SCC]

  G --> BI{Bipartite?}
  BI -->|2-color DFS/BFS| COL[2-coloring]

  G --> ALL{All-pairs shortest paths}
  ALL -->|n small| FW[Floyd-Warshall]

  G --> MST{Need minimum spanning tree?}
  MST -->|Yes| PRIM[Prim or Kruskal + UF]

  G --> DAG{DAG: ordering / deps}
  DAG --> TS[Kahn or DFS topo stack]

  G --> FLOW{Max flow / matching?}
  FLOW --> FF[Dinic / Ford-Fulkerson family]

  BFS --> GRID[Grid = implicit graph; 4/8 dirs; multisource BFS]
```

**Grid shortcuts**

- **Multi-source BFS**: distance to nearest 0, rotting oranges.
- **0–1 BFS**: binary weights on edges.
- **Flood fill / DFS**: islands, painting, connected components.
- **State graph**: position + extra state (keys, bitmask) → BFS/shortest path.

---

## 5. Trees (binary and N-ary)

```mermaid
flowchart TD
  T[Tree problem] --> PROP{BST property used?}
  PROP -->|Yes| BST[Inorder sorted / bound validation / successor]
  PROP -->|No| GEN[General tree]

  GEN --> PATH{Path from root / downward only?}
  PATH -->|Yes| DFS1[DFS return values to parent]
  PATH -->|Any path u–v| DIA[Diameter-style: max through node]

  GEN --> LEV{Level-by-level?}
  LEV -->|Yes| BFS[BFS queue]

  GEN --> LCA{LCA / distance between nodes?}
  LCA --> UP[Lifting / Euler + RMQ / parent pointers]

  GEN --> SER{Serialize / clone?}
  SER --> TRV[Preorder + marker or inorder + postorder map]

  GEN --> SUB{Subtree aggregate?}
  SUB --> POST[Postorder accumulate]
```

---

## 6. Dynamic programming (when recursion repeats subproblems)

```mermaid
flowchart TD
  DP[Smells like DP?] --> Q1{Optimal substructure + overlapping subproblems?}
  Q1 -->|No| GREEDY[Greedy or other]
  Q1 -->|Yes| Q2{State dimensions?}

  Q2 -->|1D index| D1[Linear DP: Fib-style / climb stairs / house robber]
  Q2 -->|2D grid| G2[Grid DP: unique paths / min path sum]
  Q2 -->|2D substring| S2[LCS / edit distance / palindrome substring]
  Q2 -->|Interval l..r| INT[Interval DP: burst balloons / matrix chain]
  Q2 -->|Capacity + items| KNAP[0/1 or unbounded knapsack]
  Q2 -->|Digits + tight bound| DIG[Digit DP]
  Q2 -->|Small set mask| BM[Bitmask DP / TSP-style]
  Q2 -->|Tree rooted| TD[Tree DP: rerooting optional]

  D1 --> OPT[Optimize space: rolling array if only last k rows matter]
```

**Recognition hooks**

- **“Number of ways”** → often DP or combinatorics with modulus.
- **“Minimum / maximum”** with choices → DP or greedy after proof.
- **LIS**: `O(n log n)` patience sorting / binary search on tails.
- **Knapsack**: bounded variants → binary lifting on items or monotone queue optimization (advanced).

---

## 7. Backtracking and combinatorial search

```mermaid
flowchart TD
  BK[Generate / count arrangements] --> S{Structure}
  S --> SUB[Subsets: include / exclude]
  S --> PERM[Permutations: swap or used[]]
  S --> COMB[Combinations: start index to avoid duplicates]
  S --> BOARD[N-Queens / Sudoku: prune aggressively]

  SUB --> DUP{Duplicates in input?}
  DUP -->|Yes| SORT[Sort + skip equal neighbors]
```

Use when `n` is small and constraints are **logical** (sudoku rules), not when a closed form or DP exists.

---

## 8. Binary search (not only on sorted arrays)

```mermaid
flowchart TD
  BS[Binary search entry] --> A{Classic sorted array?}
  A -->|Yes| SA[Lower/upper bound / rotated split / peak]
  A -->|No| ANS[Search on answer space]

  ANS --> MONO{Feasible(x) monotone?}
  MONO -->|Yes| MINMAX[Minimize max / maximize min templates]
  MONO -->|No| REFINE[Reformulate or different approach]

  SA --> ROT[Compare mid with end for pivot]
```

**On-answer checklist**

1. Define `check(x)` (can we achieve requirement with threshold `x`?).
2. Prove monotonicity: if `x` works, does `x+1` work (or the dual)?
3. Pick `lo, hi` carefully (inclusive vs exclusive bounds).

---

## 9. Heaps, order statistics, and scheduling

```mermaid
flowchart TD
  H[Top-k / streaming / scheduling] --> K{Which k?}
  K -->|Largest k| MINH[Min-heap of size k]
  K -->|Smallest k| MAXH[Max-heap of size k]
  K -->|Median| TWO[Two heaps: low max + high min]
  K -->|Merge sorted streams| MH[Merge k: heap of heads]

  H --> SCH{Interval / meeting rooms?}
  SCH --> SWEEP[Sweep line + heap by end time]
```

---

## 10. Data structure design & heavy queries

```mermaid
flowchart TD
  D[Design DS with ops] --> Q{Operations?}
  Q -->|Prefix sum + point update| BIT[Fenwick / BIT]
  Q -->|Range sum / min + updates| SEG[Segment tree / lazy where needed]
  Q -->|Freq / order| BAL[Balanced BST / sorted containers / indexed tree]
  Q -->|Connectivity dynamic| DSU[Union-Find + rollback optional]
  Q -->|Recency| LRU[Hash map + doubly linked list]
  Q -->|Min stack / queue| AUX[Auxiliary stacks / monotone deque]
```

---

## 11. Math, number theory, and bit tricks

```mermaid
flowchart TD
  M[Math / bits] --> NT{Divisors / primes / gcd?}
  NT -->|Yes| PM[Sieve / factorization / Euclidean gcd]

  M --> MOD{Modular inverse / combinatorics?}
  MOD --> FC[Fermat little / extended Euclid / precompute factorials]

  M --> XOR{XOR / parity / uniqueness?}
  XOR --> X1[Single number tricks / bitmask basis]

  M --> ENUM{Enumerate powers / subsets?}
  ENUM --> BP[Bit masks for n ≤ ~20]
```

---

## 12. Strings (beyond two pointers)

| Symptom | Pattern |
|--------|---------|
| Repeated pattern / substring search | KMP, Z-function, rolling hash |
| Many queries on same text | Suffix array / automaton (advanced) |
| Palindrome centers | Expand around center, Manacher (linear palindrome) |
| Lexicographic rank | Factorial numbering / combinatorics |

---

## 13. Trie and prefix structures

```mermaid
flowchart TD
  TR[Trie?] --> P{Queries by prefix?}
  P -->|Yes| T1[26-way trie or compressed trie]
  P -->|XOR max path| T2[Binary trie 0/1 children]
  P -->|Autocomplete + frequency| T3[Trie node counts + DFS prune]
```

---

## 14. Greedy (only after a proof sketch)

```mermaid
flowchart TD
  GR[Greedy candidate] --> E{Exchange argument / matroid?}
  E -->|Clear locally optimal extends| OK[Sort + one-pass / interval pick]
  E -->|Unclear| TRY[Try counterexample / DP first]

  OK --> INTG[Intervals: sort by end time / start depending on problem]
```

If a simple counterexample breaks the greedy step, switch to DP or exhaustive search for small `n`.

---

## 15. Endgame: verify before you code

```mermaid
flowchart TD
  V[Before coding] --> V1[Complexity matches constraints?]
  V1 --> V2[Integer overflow / mod?]
  V2 --> V3[Empty / single / all equal / max values]
  V3 --> V4[Off-by-one on indices / inclusive bounds]
  V4 --> V5[Mutating input allowed? Copy if not]
```

---

## 16. Pattern → template map (exhaustive checklist)

Use as a **coverage list**; tick what applies, then combine.

**Linear structures**

- [ ] Two pointers (opposite / same direction)
- [ ] Sliding window (fixed / variable)
- [ ] Prefix / suffix sums, difference array
- [ ] Hash map / set (frequency, complement, dedupe)
- [ ] Sorting + custom comparator / coordinate compression
- [ ] Monotonic stack / deque
- [ ] Binary search (array / on answer)
- [ ] Quickselect / nth element
- [ ] Merge intervals / sweep line
- [ ] Cyclic sort / “each index owns a value” tricks

**Linked structures**

- [ ] Fast and slow pointers (cycle, middle, k-from-end)
- [ ] Dummy node for edge cases
- [ ] In-place reversal (iterative / recursive)

**Trees**

- [ ] DFS (pre / in / post), return info to parent
- [ ] BFS level order
- [ ] BST invariants, successor / predecessor
- [ ] LCA (binary lifting / parent map / Euler tour)
- [ ] Serialization / deserialization

**Graphs**

- [ ] BFS / multi-source BFS / 0–1 BFS
- [ ] Dijkstra
- [ ] Bellman-Ford (negative edges)
- [ ] Floyd-Warshall (small `n`, all pairs)
- [ ] Topo sort (Kahn / DFS)
- [ ] Union-Find (components, Kruskal)
- [ ] Bipartite check
- [ ] SCC (Tarjan / Kosaraju)
- [ ] MST (Prim / Kruskal)
- [ ] Max flow / matching (when “assignment” is network flow)

**Dynamic programming & search**

- [ ] Linear / grid / interval / digit / bitmask / tree DP
- [ ] Knapsack variants
- [ ] Backtracking with pruning
- [ ] Meet-in-the-middle (split array in half, `~2^(n/2)`)

**Advanced / contest-adjacent**

- [ ] Segment tree / Fenwick
- [ ] Trie / binary trie
- [ ] Sparse table (RMQ static)
- [ ] Line sweep with heap
- [ ] String algorithms (KMP, hashing, Manacher)

---

## 17. How to combine patterns (real problems)

```mermaid
flowchart LR
  A[Problem] --> B[Primary structure]
  B --> C[Secondary tool]
  C --> D[Verify complexity]

  subgraph examples
  E[Shortest path on grid] --> E1[BFS + state bitmask]
  F[Schedule tasks] --> F1[Topo + heap for order]
  G[Subarray with at most K distinct] --> G1[Sliding window + hash map]
  end
```

Typical stacks: **graph + heap** (Dijkstra), **topo + priority** (course schedule III style), **binary search + greedy check**, **DFS + memo** (grid DP), **union-find + Kruskal**.

---

## 18. Suggested drill order (optional)

1. Arrays: two pointers, sliding window, prefix sums.
2. Binary search: sorted variants + on answer.
3. Trees: traversal + BST + path problems.
4. Graphs: BFS, DFS, topo, Dijkstra, UF.
5. DP: linear → grid → knapsack → interval.
6. Heaps, trie, segment tree / BIT as needed for gaps.

---

*This file is a living map: add links to your own solutions under `leetcode/` or `graph/` when a pattern clicks.*
