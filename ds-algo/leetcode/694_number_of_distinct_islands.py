from collections import deque
from typing import List
class Solution1: 
    def countDistinctIslands(self, grid : List[List[int]]) -> int:
        # code here
        row_size = len(grid)
        cell_size = len(grid[0])
        visited = [[False for i in range(cell_size)] for j in range(row_size)]
        directions = ((1,0), (0,1), (-1,0), (0,-1))
        queue = deque()
        island_set = set()
        for i in range(row_size):
            for j in range(cell_size):
                if grid[i][j] == 1 and not visited[i][j]:
                    current_set = []
                    visited[i][j] = True
                    queue.append((i,j))
                    current_set.append((0,0))
                    while queue:
                        e,f = queue.popleft()
                        for de, df in directions:
                            newe = e + de
                            newf = f + df
                            if 0 <= newe < row_size and 0 <= newf < cell_size and grid[newe][newf] == 1 and not visited[newe][newf]:
                                visited[newe][newf] = True
                                current_set.append((newe - i,newf - j))
                                queue.append((newe, newf))
                    current_set.sort()
                    shape = tuple(current_set)
                    if shape not in island_set:
                        island_set.add(shape)
        
        return len(island_set)
