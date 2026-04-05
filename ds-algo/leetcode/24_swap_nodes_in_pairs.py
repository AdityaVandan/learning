from typing import Optional

# Definition for singly-linked list.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
class Solution1: # recrusion O(N) O(N)
    def recursion(self, current, next):
        if current is None: return None
        if next is None: return current
        
        current.next = self.recursion(next.next, next.next.next if next.next is not None else None)
        next.next = current
        return next

    def swapPairs(self, head: Optional[ListNode]) -> Optional[ListNode]:
        if head is None: return None
        return self.recursion(head,head.next)