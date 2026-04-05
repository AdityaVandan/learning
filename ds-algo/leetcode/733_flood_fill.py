from collections import deque
from typing import List


class Solution: # bfs O(R*C)
    def floodFill(self, image: List[List[int]], sr: int, sc: int, color: int) -> List[List[int]]:
        if color == image[sr][sc]: return image
        directions = ((-1,0), (0,-1), (1,0), (0,1))
        queue =deque()
        queue.append((sr,sc))
        matrix_size = len(image)
        row_size = len(image[0])
        previous_color = image[sr][sc]
        image[sr][sc] = color
        while len(queue) > 0:
            noder, nodec = queue.popleft()
            for direction in directions:
                newr = direction[0]+noder
                newc = direction[1]+nodec
                if newr >= 0 and newr < matrix_size and newc >= 0 and newc < row_size and image[newr][newc] == previous_color:
                    image[newr][newc] = color
                    queue.append((newr, newc))
        return image


class Solution: # dfs stack O(R*C)
    def floodFill(self, image: List[List[int]], sr: int, sc: int, color: int) -> List[List[int]]:
        if color == image[sr][sc]: return image
        directions = ((-1,0), (0,-1), (1,0), (0,1))
        stack =[]
        stack.append((sr,sc))
        matrix_size = len(image)
        row_size = len(image[0])
        previous_color = image[sr][sc]
        while len(stack) > 0:
            noder, nodec = stack.pop()
            image[noder][nodec] = color
            for direction in directions:
                newr = direction[0]+noder
                newc = direction[1]+nodec
                if newr >= 0 and newr < matrix_size and newc >= 0 and newc < row_size and image[newr][newc] == previous_color:
                    stack.append((newr, newc))
        return image

class Solution: # dfs recursion O(R*C)
    def __init__(self):
        self.directions = ((-1,0), (0,-1), (1,0), (0,1))
    def recursion(self, image, sr,sc, color, previous_color):
        if image[sr][sc] == color: return
        image[sr][sc] = color
        for direction in self.directions:
            newr = direction[0]+sr
            newc = direction[1]+sc
            if newr >= 0 and newr < len(image) and newc >= 0 and newc < len(image[0]) and image[newr][newc] == previous_color:
                self.recursion(image,newr,newc,color,previous_color)

    def floodFill(self, image: List[List[int]], sr: int, sc: int, color: int) -> List[List[int]]:
        if color == image[sr][sc]: return image
        previous_color = image[sr][sc]
        self.recursion(image,sr,sc, color, previous_color)
        return image