from collections import deque
class Solution: # bfs queue O(V + E)
    def shortestPath(self, V, edges, src):
        # code here
        graph = [[] for i in range(V)]
        source_distance = [-1 for i in range(V)]
        queue = deque()
        queue.append(src)
        source_distance[src] = 0
        
        for u, v in edges:
            graph[u].append(v)
            graph[v].append(u)
        
        while queue:
            u = queue.popleft()
            
            for v in graph[u]:
                if source_distance[v] == -1 or source_distance[v] > source_distance[u] + 1:
                    source_distance[v] = source_distance[u] + 1
                    queue.append(v)
        
        return source_distance
        
