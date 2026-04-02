# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, x):
#         self.val = x
#         self.next = None

class Solution: # O(N)
    def hasCycle(self, head: Optional[ListNode]) -> bool:
        double_pointer = pointer = head
        while double_pointer and double_pointer.next:
            pointer = pointer.next
            double_pointer = double_pointer.next.next
            if pointer == double_pointer:
                return True

        return False
