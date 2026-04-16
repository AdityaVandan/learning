def kosaraju(adj):
    """
    Strongly connected components of a directed graph (Kosaraju's algorithm).

    adj[u] = neighbors v with u -> v.

    Returns a list of components; each component is a list of vertices.
    """
    n = len(adj)
    visited = [False] * n
    order = []

    def dfs1(u):
        visited[u] = True
        for v in adj[u]:
            if not visited[v]:
                dfs1(v)
        order.append(u)

    for i in range(n):
        if not visited[i]:
            dfs1(i)

    radj = [[] for _ in range(n)]
    for u in range(n):
        for v in adj[u]:
            radj[v].append(u)

    visited = [False] * n
    components = []

    def dfs2(u, acc):
        visited[u] = True
        acc.append(u)
        for v in radj[u]:
            if not visited[v]:
                dfs2(v, acc)

    for u in reversed(order):
        if not visited[u]:
            comp = []
            dfs2(u, comp)
            components.append(comp)

    return components
