# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
class Solution:
    def createBinaryTree(self, descriptions: List[List[int]]) -> Optional[TreeNode]:
        cache = {}
        child_cache = {}
        for relation in descriptions:
            parent_value, child_value, is_left = relation
            if child_cache.get(parent_value, None) == None:
                child_cache[parent_value] = False

            if child_cache.get(child_value, None) == None:
                child_cache[child_value] = True

            parent_node = cache.get(parent_value, None)
            if not parent_node:
                parent_node = TreeNode(parent_value)
                cache[parent_value] = parent_node
            
            child_node = cache.get(child_value, None)
            if not child_node:
                child_node = TreeNode(child_value)
                cache[child_value] = child_node

            if is_left == 1:
                parent_node.left = child_node
            if is_left == 0:
                parent_node.right = child_node
        
        root = None
        for node_value, is_child in child_cache.items():
            if not is_child:
                root = cache[node_value]
                break
        
        return root
