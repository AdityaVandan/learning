from collections import deque


class Solution1:
    def dfs(self, node, edges, visited, path_visited):
        visited[node] = True
        path_visited[node] = True
        
        for neighbour in edges[node]:
            if not visited[neighbour]:
                if self.dfs(neighbour, edges, visited, path_visited):
                    return True
            elif path_visited[neighbour]:
                return True
        
        path_visited[node] = False  # backtrack
        return False

    def isCyclic(self, V, edges):
        visited = [False] * V
        path_visited = [False] * V
        
        for i in range(V):
            if not visited[i]:
                if self.dfs(i, edges, visited, path_visited):
                    return True
        
        return False

class Solution2:  # BFS (Kahn) O(V + E) O(V)
    """
    Directed cycle iff topological sort cannot consume all vertices:
    repeatedly remove indegree-0 nodes; leftover implies a directed cycle.
    """

    def isCycle(self, V, adj):
        indeg = [0] * V
        for u in range(V):
            for v in adj[u]:
                indeg[v] += 1

        q = deque(i for i in range(V) if indeg[i] == 0)
        seen = 0

        while q:
            u = q.popleft()
            seen += 1
            for v in adj[u]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    q.append(v)

        return seen != V


class Solution3:  # DFS three-color (WHITE/GRAY/BLACK) O(V + E) O(V)
    """
    Three-color DFS:
    - WHITE: unvisited
    - GRAY: currently in recursion stack (active path)
    - BLACK: fully processed

    A directed cycle exists iff we see an edge to a GRAY vertex.
    """

    def isCyclic(self, V, edges):
        WHITE, GRAY, BLACK = 0, 1, 2
        color = [WHITE] * V

        def dfs(u):
            color[u] = GRAY
            for v in edges[u]:
                if color[v] == GRAY:
                    return True
                if color[v] == WHITE and dfs(v):
                    return True
            color[u] = BLACK
            return False

        for i in range(V):
            if color[i] == WHITE and dfs(i):
                return True
        return False
