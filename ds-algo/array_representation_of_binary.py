# Definition for a binary tree node.
class TreeNode(object):
    def __init__(self, x):
        self.val = x
        self.left = None
        self.right = None

class Codec:

    def serialize(self, root):
        """Encodes a tree to a single string.
        
        :type root: TreeNode
        :rtype: str
        """
        if root == None: return ""
        arr = [' ']*1000000
        stack = []
        stack.append((root, 0))
        while len(stack) > 0:
            node, index = stack.pop()
            arr[index] = str(node.val)

            if node.left:
                stack.append((node.left, 2*index+1))
            if node.right:
                stack.append((node.right, 2*index+2))
        return ','.join(arr)

    def deserialize(self, data):
        """Decodes your encoded data to tree.
        
        :type data: str
        :rtype: TreeNode
        """
        if data == "": return None
        arr = data.split(",")
        stack = []
        root = TreeNode(-1)
        stack.append((root,0))
        while len(stack) > 0:
            node, index = stack.pop()

            value = None
            if arr[index] != " ": value = int(arr[index])
            node.val = value

            leftIndex = 2*index + 1
            if leftIndex < len(arr) and arr[leftIndex] != " ":
                node.left = TreeNode(-1)
                stack.append((node.left, leftIndex))
            
            rightIndex = 2*index + 2
            if rightIndex < len(arr) and arr[rightIndex] != " ":
                node.right = TreeNode(-1)
                stack.append((node.right, rightIndex))
        
        return root


        

# Your Codec object will be instantiated and called as such:
# ser = Codec()
# deser = Codec()
# ans = deser.deserialize(ser.serialize(root))