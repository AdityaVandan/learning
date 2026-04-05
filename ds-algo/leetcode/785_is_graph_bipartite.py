from collections import deque
from typing import List


class Solution1:  # DFS recursive O(V + E)
    def isBipartite(self, graph: List[List[int]]) -> bool:
        n = len(graph)
        colors = [-1] * n

        def dfs(node: int, c: int) -> bool:
            colors[node] = c
            for nei in graph[node]:
                if colors[nei] == -1:
                    if not dfs(nei, 1 - c):
                        return False
                elif colors[nei] == c:
                    return False
            return True

        for i in range(n):
            if colors[i] == -1 and not dfs(i, 0):
                return False
        return True


class Solution2:  # BFS O(V + E)
    def isBipartite(self, graph: List[List[int]]) -> bool:
        n = len(graph)
        colors = [-1] * n

        for s in range(n):
            if colors[s] != -1:
                continue
            colors[s] = 0
            q = deque([s])
            while q:
                u = q.popleft()
                for v in graph[u]:
                    if colors[v] == -1:
                        colors[v] = 1 - colors[u]
                        q.append(v)
                    elif colors[v] == colors[u]:
                        return False
        return True
