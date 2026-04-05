from collections import deque
from typing import List


class Solution:
    def updateMatrix(self, mat: List[List[int]]) -> List[List[int]]:
        row_size = len(mat)
        cell_size = len(mat[0])
        directions = ((0,-1),(-1,0),(0,1),(1,0))
        queue = deque()
        distance_cache = [[-1]*cell_size for i in range(row_size)]

        for i in range(row_size):
            for j in range(cell_size):
                if mat[i][j] == 0:
                    distance_cache[i][j] = 0
                    queue.append((i,j))
        while queue:
            i,j = queue.popleft()
            for direction in directions:
                newi = i + direction[0]
                newj = j + direction[1]
                if newi >=0 and newi<row_size and newj>=0 and newj <cell_size and distance_cache[newi][newj] == -1:
                    queue.append((newi,newj))
                    distance_cache[newi][newj] = distance_cache[i][j] + 1
        return distance_cache
