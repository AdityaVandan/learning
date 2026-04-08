import heapq


def dijkstra(adj, start):
    """
    Single-source shortest paths (non-negative edge weights).

    adj[u] is a list of (v, weight) pairs. Vertices are 0 .. len(adj) - 1.

    Returns (dist, parent) where dist[v] is shortest distance from start to v,
    and parent[v] is the previous vertex on a shortest path (-1 for start /
    unreachable).
    """
    n = len(adj)
    dist = [float("inf")] * n
    parent = [-1] * n
    dist[start] = 0
    pq = [(0, start)]

    while pq:
        d, u = heapq.heappop(pq)
        if d != dist[u]:
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                parent[v] = u
                heapq.heappush(pq, (nd, v))

    return dist, parent
