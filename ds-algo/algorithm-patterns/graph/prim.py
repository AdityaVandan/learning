import heapq


def prim(adj):
    """
    Minimum spanning forest (Prim). adj[u] = [(v, weight), ...] undirected.

    Each undirected edge should appear in both endpoints' lists (or the
    algorithm only sees half-edges from listed sides).

    Returns list of (u, v, weight) tree edges, one spanning tree per component.
    """
    n = len(adj)
    in_tree = [False] * n
    mst = []
    pq = []

    for start in range(n):
        if in_tree[start]:
            continue
        heapq.heappush(pq, (0, -1, start))
        while pq:
            w, u, v = heapq.heappop(pq)
            if in_tree[v]:
                continue
            in_tree[v] = True
            if u != -1:
                mst.append((u, v, w))
            for to, wt in adj[v]:
                if not in_tree[to]:
                    heapq.heappush(pq, (wt, v, to))

    return mst
