from collections import deque
from typing import List


class Solution1: # dfs stack O(R*C)
    def numEnclaves(self, grid: List[List[int]]) -> int:
        stack = []
        row_size = len(grid)
        cell_size = len(grid[0])
        directions = ((1,0), (0,1), (-1,0), (0,-1))
        visited = [[False for j in range(cell_size)] for i in range(row_size)]
        total = 0
        for i in range(row_size):
            for j in range(cell_size):
                if grid[i][j] == 1:
                    total += 1
                    if(i == 0 or j == 0 or i == row_size - 1 or j == cell_size - 1):
                        stack.append((i,j))
        
        while stack:
            i, j = stack.pop()
            if visited[i][j]: continue
            total -= 1
            visited[i][j] = True
            for di, dj in directions:
                newi = i + di
                newj = j + dj
                if 0 <= newi < row_size and 0 <= newj < cell_size and grid[newi][newj] == 1 and not visited[newi][newj]:
                    stack.append((newi, newj))
                
        return total

class Solution2: # dfs recursion O(R*C)
    def numEnclaves(self, grid: List[List[int]]) -> int:
        row_size = len(grid)
        cell_size = len(grid[0])
        directions = ((1,0), (0,1), (-1,0), (0,-1))
        visited = [[False for _ in range(cell_size)] for _ in range(row_size)]
        total = 0

        def dfs(i, j):
            if visited[i][j]:
                return 0
            
            visited[i][j] = True
            count = 1  # this cell contributes to removal

            for di, dj in directions:
                ni, nj = i + di, j + dj
                if (
                    0 <= ni < row_size and
                    0 <= nj < cell_size and
                    grid[ni][nj] == 1 and
                    not visited[ni][nj]
                ):
                    count += dfs(ni, nj)

            return count

        # Count total land and start DFS from boundary land
        for i in range(row_size):
            for j in range(cell_size):
                if grid[i][j] == 1:
                    total += 1
                    if i == 0 or j == 0 or i == row_size - 1 or j == cell_size - 1:
                        total -= dfs(i, j)  # remove boundary-connected land

        return total

class Solution3: # bfs queue O(R*C)
    def numEnclaves(self, grid: List[List[int]]) -> int:
        queue = deque()
        row_size = len(grid)
        cell_size = len(grid[0])
        directions = ((1,0), (0,1), (-1,0), (0,-1))
        visited = [[False for j in range(cell_size)] for i in range(row_size)]
        total = 0

        for i in range(row_size):
            for j in range(cell_size):
                if grid[i][j] == 1:
                    total += 1
                    if (i == 0 or j == 0 or i == row_size - 1 or j == cell_size - 1):
                        queue.append((i, j))

        while queue:
            i, j = queue.popleft()   # <-- only real change
            if visited[i][j]:
                continue

            total -= 1
            visited[i][j] = True

            for di, dj in directions:
                newi = i + di
                newj = j + dj
                if (
                    0 <= newi < row_size and
                    0 <= newj < cell_size and
                    grid[newi][newj] == 1 and
                    not visited[newi][newj]
                ):
                    queue.append((newi, newj))

        return total

