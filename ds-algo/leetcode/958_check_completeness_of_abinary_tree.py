# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

class Solution:
    def isCompleteTree(self, root: Optional[TreeNode]) -> bool:
        if not root: return
        queue = deque()
        queue.append(root)
        level_order = []
        while len(queue) > 0:
            node = queue.popleft()
            if node:
                level_order.append(node)
                queue.append(node.left)
                queue.append(node.right)
            else:
                level_order.append(None)
            
        
        is_none_in_between = False
        for val in level_order:
            if val is None: is_none_in_between = True
            elif is_none_in_between:
                return False
        
        return True