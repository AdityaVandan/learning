# Definition for a binary tree node.
# class TreeNode(object):
#     def __init__(self, x):
#         self.val = x
#         self.left = None
#         self.right = None

class Codec:

    def serialize(self, root):
        """Encodes a tree to a single string.
        
        :type root: TreeNode
        :rtype: str
        """
        if root == None: return ""
        arr = []
        queue = deque()
        queue.append(root)
        while len(queue) > 0:
            node = queue.popleft()
            if node:
                arr.append(str(node.val))
                queue.append(node.left)
                queue.append(node.right)
            else: arr.append("")
        return ','.join(arr)

    def deserialize(self, data):
        """Decodes your encoded data to tree.
        
        :type data: str
        :rtype: TreeNode
        """
        if data == "": return None
        arr = data.split(",")
        queue = deque()
        root = TreeNode(arr[0])
        queue.append((root))
        index = 1
        while len(queue) > 0:
            node = queue.popleft()

            if arr[index] != "":
                node.left = TreeNode(arr[index])
                queue.append(node.left)
            index+=1
            if arr[index] != "":
                node.right = TreeNode(arr[index])
                queue.append(node.right)
            index+=1
        return root


        

# Your Codec object will be instantiated and called as such:
# ser = Codec()
# deser = Codec()
# ans = deser.deserialize(ser.serialize(root))