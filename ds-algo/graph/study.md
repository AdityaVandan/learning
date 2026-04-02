# Graphs
N = number of nodes
E = number of edges

### Convention and Represntation
- conventions: nodes, edges, node-edge relationship
- representation: 2d array (adjacency matrix), node-edge relation (adjacency list)
- degree: number of neighbours


## Breadth first search
- uses queue
- visited is marked when neighbours are visited (not when node is taken out from queue like in dfs)
- only enqueue neighbours which are not visited, (after settings their visited as true)
For directed Graph
- Space complexity: O(N)
- Time complexity: O(N + 2E)

## Depth first search
- uses stack
- visited is marked when taken out of stack
- check if visited before putting into stack again
For directed Graph
- Space complexity: O(N)
- Time complexity: O(N + 2E)

## Number of connected components:
- dfs using every node as source

##