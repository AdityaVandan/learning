#User function Template for python3

from typing import List
from collections import deque


def shortestPath(self, V: int, E: int, edges: List[List[int]]) -> List[int]:
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
