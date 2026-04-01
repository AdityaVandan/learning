# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def mergeKLists(self, lists: List[Optional[ListNode]]) -> Optional[ListNode]:
        priority_queue = []
        counter = itertools.count()
        for node in lists:
            if node:
                heapq.heappush(priority_queue, (node.val, next(counter), node))
        
        pre_root = ListNode(-1) # dummy node creation
        current_node = pre_root
        while priority_queue:
            _,_,node = heapq.heappop(priority_queue)
            current_node.next = node
            current_node = node
            if node.next is not None: heapq.heappush(priority_queue,(node.next.val, next(counter),node.next))

        return pre_root.next
