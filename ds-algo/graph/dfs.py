def dfs_recursive(adj, start, visited=None, order=None):
    """
    Depth-first traversal from `start` (recursive).

    `adj` is an adjacency list. Vertices are 0 .. len(adj) - 1.

    Returns nodes in preorder (visit before children in adjacency order).
    """
    if visited is None:
        visited = [False] * len(adj)
        order = []

    visited[start] = True
    order.append(start)

    for v in adj[start]:
        if not visited[v]:
            dfs_recursive(adj, v, visited, order)

    return order


def dfs_stack(adj, start):
    """
    Depth-first traversal from `start` (explicit stack).

    Neighbors are pushed in reverse order so the first neighbor in adj[start]
    is explored next, matching dfs_recursive's preorder for the same graph.
    """
    n = len(adj)
    visited = [False] * n
    order = []
    stack = [start]

    while stack:
        u = stack.pop()
        if visited[u]:
            continue
        visited[u] = True
        order.append(u)
        for v in reversed(adj[u]):
            if not visited[v]:
                stack.append(v)

    return order
