"""Toy consistent-hash ring.

Each physical node owns V points on a circle. A key is served by the first
point at or clockwise from hash(key). Adding a node steals only the arcs its
new points land on, so most keys keep their owner.

Run from this directory:

    python3 toy.py
"""

from __future__ import annotations

import bisect
import hashlib
from collections import Counter


def hash_position(value: str) -> int:
    """Stable position on a 2^32 ring.

    MD5 is used so the same key lands on the same point in every process.
    CPython's built-in hash() is salted with PYTHONHASHSEED and would
    reshuffle the ring on every restart.
    """
    digest = hashlib.md5(value.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


class ConsistentHashRing:
    """Sorted circle of virtual-node points.

    Lookup is a binary search for the clockwise successor. A list keeps that
    search obvious. Inserting into the list is linear; a balanced tree
    (Java TreeMap is the usual production sketch) would make insert logarithmic.
    The partition rule is the same either way.
    """

    def __init__(self, virtual_nodes: int = 1) -> None:
        if virtual_nodes < 1:
            raise ValueError("virtual_nodes must be >= 1")
        self.virtual_nodes = virtual_nodes
        self._order: list[str] = []
        self._positions: list[int] = []
        self._owners: list[str] = []

    @property
    def nodes(self) -> list[str]:
        return list(self._order)

    def add_node(self, node: str) -> None:
        """Place `virtual_nodes` points for this physical node on the ring."""
        if node in self._order:
            raise ValueError(f"node already on ring: {node}")
        self._order.append(node)
        for replica in range(self.virtual_nodes):
            # The vnode name is part of the contract. Every client must hash
            # the same string or they will disagree about ownership.
            position = hash_position(f"{node}#{replica}")
            index = bisect.bisect_left(self._positions, position)
            if index < len(self._positions) and self._positions[index] == position:
                # Two points hit the same slot. Keep the earlier one so each
                # slot has a single successor. Negligible at toy scale on 2^32.
                continue
            self._positions.insert(index, position)
            self._owners.insert(index, node)

    def remove_node(self, node: str) -> None:
        """Drop every point owned by this physical node. Arcs merge clockwise."""
        if node not in self._order:
            raise KeyError(node)
        self._order.remove(node)
        kept = [
            (position, owner)
            for position, owner in zip(self._positions, self._owners)
            if owner != node
        ]
        self._positions = [position for position, _ in kept]
        self._owners = [owner for _, owner in kept]

    def get_node(self, key: str) -> str:
        """Physical node that owns this key: the clockwise successor."""
        index = self._successor_index(hash_position(key))
        return self._owners[index]

    def get_replicas(self, key: str, count: int) -> list[str]:
        """Preference list: the next `count` distinct physical nodes clockwise.

        Walking virtual nodes of a node already chosen is skipped. Dynamo-style
        replication uses this list; the first entry is the primary from get_node.
        """
        if count < 1:
            raise ValueError("count must be >= 1")
        if count > len(self._order):
            raise ValueError("not enough distinct nodes for the requested replicas")
        index = self._successor_index(hash_position(key))
        chosen: list[str] = []
        seen: set[str] = set()
        for _ in range(len(self._positions)):
            owner = self._owners[index]
            if owner not in seen:
                seen.add(owner)
                chosen.append(owner)
                if len(chosen) == count:
                    return chosen
            index = (index + 1) % len(self._positions)
        return chosen

    def _successor_index(self, position: int) -> int:
        if not self._positions:
            raise RuntimeError("ring has no nodes")
        # First point at or clockwise from `position`. Past the last point,
        # the circle wraps and the first point owns the key.
        index = bisect.bisect_left(self._positions, position)
        if index == len(self._positions):
            return 0
        return index


def modulo_owner(key: str, nodes: list[str]) -> str:
    """hash(key) % N. Included so the demo can count how much this remaps."""
    if not nodes:
        raise RuntimeError("no nodes")
    return nodes[hash_position(key) % len(nodes)]


def _owners(assign, keys: list[str]) -> dict[str, str]:
    return {key: assign(key) for key in keys}


def _moved(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return [key for key in before if before[key] != after[key]]


def _print_balance(title: str, assignment: dict[str, str]) -> None:
    counts = Counter(assignment.values())
    total = sum(counts.values())
    print(title)
    for node, count in sorted(counts.items()):
        print(f"  {node}: {count:5d}  ({count / total:6.1%})")
    smallest, largest = min(counts.values()), max(counts.values())
    print(f"  max/min load: {largest / smallest:.2f}")


def _print_move(title: str, moved: list[str], total: int) -> None:
    print(f"{title}: {len(moved)}/{total} keys moved ({len(moved) / total:.1%})")


def demo() -> None:
    keys = [f"user:{i}" for i in range(10_000)]
    base = ["cache-a", "cache-b", "cache-c"]

    print("Modulo hashing remaps most keys when the node count changes.")
    print("Consistent hashing remaps about 1/(N+1), onto the node that joined.\n")

    modulo_before = _owners(lambda key: modulo_owner(key, base), keys)
    modulo_after = _owners(lambda key: modulo_owner(key, base + ["cache-d"]), keys)
    _print_move("modulo, 3 -> 4 nodes", _moved(modulo_before, modulo_after), len(keys))

    for virtual_nodes in (1, 64):
        ring = ConsistentHashRing(virtual_nodes=virtual_nodes)
        for node in base:
            ring.add_node(node)
        before = _owners(ring.get_node, keys)
        ring.add_node("cache-d")
        after = _owners(ring.get_node, keys)
        moved = _moved(before, after)
        print()
        _print_move(
            f"consistent hash, V={virtual_nodes}, 3 -> 4 nodes",
            moved,
            len(keys),
        )
        landed_on_new = {after[key] for key in moved}
        if landed_on_new != {"cache-d"} and moved:
            raise SystemExit(f"moved keys did not all land on cache-d: {landed_on_new}")
        print("  every moved key is now owned by cache-d")
        _print_balance("  ownership after the join:", after)

    print("\nRemoving a node merges its arcs into the clockwise successor.")
    print("One point per node dumps that load on a single neighbor.")
    print("Many virtual nodes spread it.\n")

    for virtual_nodes in (1, 64):
        ring = ConsistentHashRing(virtual_nodes=virtual_nodes)
        for node in base + ["cache-d"]:
            ring.add_node(node)
        before = _owners(ring.get_node, keys)
        owned = [key for key in keys if before[key] == "cache-b"]
        ring.remove_node("cache-b")
        destinations = Counter(ring.get_node(key) for key in owned)
        print(f"V={virtual_nodes}: {len(owned)} keys left cache-b and went to:")
        for node, count in sorted(destinations.items()):
            print(f"  {node}: {count}")
        if virtual_nodes == 1 and len(destinations) != 1:
            raise SystemExit("a single point should have one clockwise successor")
        if virtual_nodes > 1 and len(destinations) < 2:
            raise SystemExit("virtual nodes should spread a removal across neighbors")

    ring = ConsistentHashRing(virtual_nodes=64)
    for node in base:
        ring.add_node(node)
    replicas = ring.get_replicas("user:42", 3)
    print(f"\npreference list for user:42: {' -> '.join(replicas)}")
    if replicas[0] != ring.get_node("user:42"):
        raise SystemExit("primary replica must match get_node")
    if len(replicas) != len(set(replicas)):
        raise SystemExit("preference list repeated a physical node")


if __name__ == "__main__":
    demo()
