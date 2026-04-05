from typing import List, Optional

# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
class Solution1: # recursion O(N) O(N)
    def recursion(self, nums, left, right):
        if left > right: return None
        mid = (left + right) // 2
        node = TreeNode(nums[mid])
        node.left = self.recursion(nums, left, mid - 1)
        node.right = self.recursion(nums, mid + 1, right)
        return node
    def sortedArrayToBST(self, nums: List[int]) -> Optional[TreeNode]:
        return self.recursion(nums,0, len(nums)-1)

class Solution2: # stack O(N) O(log(N))
    def sortedArrayToBST(self, nums: List[int]) -> Optional[TreeNode]:
        stack = []
        root = TreeNode(-1)
        stack.append((root,0, len(nums) - 1))
        while len(stack) > 0:
            node, low, high = stack.pop()
            mid = (low + high) // 2
            node.val = nums[mid]
            
            if low <= mid-1:
                node.left=TreeNode(-1)
                stack.append((node.left, low, mid - 1))
            if high >= mid+1:
                node.right=TreeNode(-1)
                stack.append((node.right, mid + 1, high))
        return root
