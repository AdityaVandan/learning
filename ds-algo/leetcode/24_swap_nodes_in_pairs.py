# Definition for singly-linked list.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
class Solution1: # recrusion O(N) O(N)
    def recursion(self, current, next):
        if current is None: return None
        if next is None: return current
        arg1 = next.next
        arg2 = next.next.next if next.next is not None else None
        
        next.next = current
        current.next = self.recursion(arg1, arg2)
        return next

    def swapPairs(self, head: Optional[ListNode]) -> Optional[ListNode]:
        if head is None: return None
        return self.recursion(head,head.next)