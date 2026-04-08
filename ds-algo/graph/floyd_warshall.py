def make_dist_matrix(n, edges, directed=True):
    """
    Build an n x n distance matrix from edge list edges = (u, v, w).

    Missing edges are inf; diagonal is 0. For undirected graphs, set directed=False.
    """
    g = [[float("inf")] * n for _ in range(n)]
    for i in range(n):
        g[i][i] = 0
    for u, v, w in edges:
        g[u][v] = min(g[u][v], w)
        if not directed:
            g[v][u] = min(g[v][u], w)
    return g


def floyd_warshall(dist):
    """
    All-pairs shortest paths. `dist` is an n x n matrix (copy is not mutated).

    After running, dist[i][j] is shortest distance i -> j, or inf if unreachable.
    Negative cycles (sum < 0) can make entries diverge; this implementation does
    not report them (use Bellman-Ford for single-source with negative edges).
    """
    n = len(dist)
    d = [row[:] for row in dist]

    for k in range(n):
        for i in range(n):
            if d[i][k] == float("inf"):
                continue
            for j in range(n):
                if d[k][j] == float("inf"):
                    continue
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]

    return d
