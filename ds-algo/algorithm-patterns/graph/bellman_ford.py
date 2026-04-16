def bellman_ford(n, edges, start):
    """
    Single-source shortest paths; edges may be negative. edges = (u, v, w).

    Returns (dist, ok). If ok is False, a negative cycle reachable from start
    exists and dist is not reliable.
    """
    dist = [float("inf")] * n
    dist[start] = 0

    for _ in range(n - 1):
        updated = False
        for u, v, w in edges:
            if dist[u] == float("inf"):
                continue
            nd = dist[u] + w
            if nd < dist[v]:
                dist[v] = nd
                updated = True
        if not updated:
            break

    for u, v, w in edges:
        if dist[u] == float("inf"):
            continue
        if dist[u] + w < dist[v]:
            return dist, False

    return dist, True
