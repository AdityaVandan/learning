## Problem-statement
The problem is the lack of a reliable global notion of time in distributed systems, which makes it fundamentally hard to determine the true ordering of events across different machines.

Because messages can be delayed unpredictably and physical clocks drift (and can’t be perfectly synchronized), two key problems show up:

You can’t safely infer “which event happened first” just from timestamps. A later timestamp might correspond to an earlier causally-related event (or vice versa).
Without a consistent ordering, systems can behave incorrectly, e.g., inconsistent replicas, “impossible” histories in logs/debugging, and violations of assumptions like “if A caused B, then A must be ordered before B.”
Lamport’s core contribution was to formalize this as causal (happens-before) ordering and to show how to build logical clocks that impose a consistent event order that respects causality even when real clocks can’t.

## Terminologies:
- partial ordering
- complete ordering
- total ordering
- synchronization
- obtained vs percieveed ordering by the user
- logical clocks
- eventual release and grant of a resource
- mutual exclusion

## Diagram

## Relations and Assumptions
- Every process communicating with every other process while resource acquring and release.