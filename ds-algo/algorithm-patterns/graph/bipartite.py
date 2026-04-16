from collections import deque


def is_bipartite(adj):
    """
    Return True if the undirected graph can be 2-colored.

    adj is an adjacency list; each edge should be represented at both endpoints
    for undirected graphs.
    """
    # Time: O(V + E) (each vertex/edge processed at most a constant number of times)
    # Space: O(V) for color + O(V) queue in worst case
    n = len(adj)
    color = [-1] * n

    for s in range(n):
        if color[s] != -1:
            continue
        color[s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if color[v] == -1:
                    color[v] = color[u] ^ 1
                    q.append(v)
                elif color[v] == color[u]:
                    return False

    return True


def is_bipartite_dfs(adj):
    """
    Return True if the undirected graph can be 2-colored (DFS version).

    adj is an adjacency list; each edge should be represented at both endpoints
    for undirected graphs.
    """
    # Time: O(V + E)
    # Space: O(V) for color + O(V) recursion stack in worst case
    n = len(adj)
    color = [-1] * n

    def dfs(u):
        for v in adj[u]:
            if color[v] == -1:
                color[v] = color[u] ^ 1
                if not dfs(v):
                    return False
            elif color[v] == color[u]:
                return False
        return True

    for s in range(n):
        if color[s] != -1:
            continue
        color[s] = 0
        if not dfs(s):
            return False

    return True
