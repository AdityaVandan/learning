from typing import List
from collections import deque

class Solution1: # bfs queue O(V + E)
    def shortest_path(V: int, E: int, edges: List[List[int]]) -> List[int]:
        weights = [[-1 for e in range(V)] for v in range(V)]
        for i in range(V):
            weights[i][i] = 0
        graph = [[] for i in range(V)]
        source_weight = [-1]*V
        for node, neighbour, weight in edges:
            weights[node][neighbour] = weight
            graph[node].append(neighbour)

        visited = [False]*V

        queue = deque()
        queue.append(0)
        source_weight[0] = 0
        while queue:
            node = queue.popleft()
            for neighbour in graph[node]:
                if not visited[neighbour]:
                    visited[neighbour] = True
                    source_weight[neighbour] = source_weight[node] + weights[node][neighbour]
                    queue.append(neighbour)
                elif source_weight[neighbour] != -1 and source_weight[neighbour] > source_weight[node] + weights[node][neighbour]:
                    source_weight[neighbour] = source_weight[node] + weights[node][neighbour]
                    queue.append(neighbour)
        
        return source_weight

class Solution2: # topological sort queue O(V + E)

    def shortestPath(self, V: int, E: int, edges: List[List[int]]) -> List[int]:
        indegrees = [0 for i in range(V)]
        adjacency_list = [[] for i in range(V)]
        for u,v,wgt in edges:
            indegrees[v] += 1
            adjacency_list[u].append((v, wgt))
        
        queue = deque()
        for i in range(V):
            if indegrees[i] == 0: queue.append(i)
        # queue.append(0)
        source_weight = [-1 for i in range(V)]
        source_weight[0] = 0
        while queue:
            u = queue.popleft()
            
            for v, wgt in adjacency_list[u]:
                indegrees[v] -= 1
                if source_weight[u] != -1:
                    new_calculated_wgt = source_weight[u] + wgt
                    if source_weight[v] == -1 or source_weight[v] > new_calculated_wgt: source_weight[v] = new_calculated_wgt
                if indegrees[v] == 0:
                    queue.append(v)
        
        return source_weight