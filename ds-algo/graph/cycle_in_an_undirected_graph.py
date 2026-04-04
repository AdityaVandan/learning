class Solution: # DFS O(V+E) #(V)
    def isCycle(self, V, adj):
        visited = [False] * V

        for i in range(V):
            if not visited[i]:
                stack = [(-1, i)]

                while stack:
                    prev, vertex = stack.pop()

                    if visited[vertex]:
                        continue

                    visited[vertex] = True

                    for neighbour in adj[vertex]:
                        if not visited[neighbour]:
                            stack.append((vertex, neighbour))
                        elif neighbour != prev:
                            return True

        return False

from collections import deque

class Solution: # BFS O(V+E) O(V)
    def isCycle(self, V, adj):
        visited = [False] * V

        for i in range(V):
            if not visited[i]:
                queue = deque([(i, -1)])
                visited[i] = True

                while queue:
                    node, parent = queue.popleft()

                    for neighbour in adj[node]:
                        if not visited[neighbour]:
                            visited[neighbour] = True
                            queue.append((neighbour, node))
                        elif neighbour != parent:
                            return True

        return False