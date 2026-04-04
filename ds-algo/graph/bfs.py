from collections import deque


def bfs(adj, start):
    """
    Breadth-first traversal from `start`.

    `adj` is an adjacency list: adj[u] = list of neighbors of u.
    Vertices are assumed to be indices 0 .. len(adj) - 1.

    Returns nodes in visit order (each node once).
    """
    n = len(adj)
    visited = [False] * n
    order = []
    q = deque([start])

    visited[start] = True

    while q:
        u = q.popleft()
        order.append(u)
        for v in adj[u]:
            if not visited[v]:
                visited[v] = True
                q.append(v)

    return order
