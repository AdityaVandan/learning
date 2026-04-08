from collections import deque


def topological_sort_kahn(adj):
    """
    Topological order of a DAG using Kahn's algorithm (BFS on indegree).

    adj[u] = list of v with directed edge u -> v.

    Returns a list of all vertices in topological order, or None if a cycle exists.
    """
    n = len(adj)
    indeg = [0] * n
    for u in range(n):
        for v in adj[u]:
            indeg[v] += 1

    q = deque(i for i in range(n) if indeg[i] == 0)
    order = []

    while q:
        u = q.popleft()
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)

    return order if len(order) == n else None


def topological_sort_dfs(adj):
    """
    Topological order via DFS postorder (reverse finish times).

    Returns a list in topological order, or None if a directed cycle exists.
    """
    n = len(adj)
    WHITE, GRAY, BLACK = 0, 1, 2
    state = [WHITE] * n
    stack_rev = []

    def visit(u):
        state[u] = GRAY
        for v in adj[u]:
            if state[v] == GRAY:
                return False
            if state[v] == WHITE and not visit(v):
                return False
        state[u] = BLACK
        stack_rev.append(u)
        return True

    for u in range(n):
        if state[u] == WHITE and not visit(u):
            return None

    stack_rev.reverse()
    return stack_rev
