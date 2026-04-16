import os
import sys

_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from union_find import UnionFind


def kruskal(n, edges):
    """
    Minimum spanning forest for an undirected weighted graph.

    edges is a list of (u, v, weight). Vertices are 0 .. n - 1.

    Returns a list of (u, v, weight) edges forming an MST in each connected
    component (|MST edges| = n - c where c = number of components).
    """
    edges_sorted = sorted(edges, key=lambda e: e[2])
    uf = UnionFind(n)
    mst = []
    for u, v, w in edges_sorted:
        if uf.union(u, v):
            mst.append((u, v, w))
    return mst
