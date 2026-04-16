import heapq
from collections import deque
from typing import List

class Solution: # dijkstra heap O(V log V + E log V)
    def shortestPathBinaryMatrix(self, grid: List[List[int]]) -> int:
        row_size = len(grid)
        cell_size = len(grid[0])
        if grid[0][0] == 1: return -1
        directions = ((-1,0), (0,-1), (-1,-1), (1,0), (0,1), (1,1), (1,-1), (-1,1))
        distance_matrix = [[-1 for j in range(cell_size)] for i in range(row_size)]
        queue = []
        distance_matrix[0][0] = 1
        heapq.heappush(queue, (distance_matrix[0][0], (0,0)))
        while queue:
            distance, node = heapq.heappop(queue)
            i, j = node
            for di, dj in directions:
                newi = i + di
                newj = j + dj
                if newi >=0 and newi < row_size and newj >= 0 and newj < cell_size and grid[newi][newj]== 0 and (distance_matrix[newi][newj] == -1 or distance_matrix[newi][newj] > distance_matrix[i][j] + 1):
                    distance_matrix[newi][newj] = distance_matrix[i][j] + 1
                    heapq.heappush(queue, (distance_matrix[newi][newj], (newi,newj)))
        return distance_matrix[row_size - 1][cell_size - 1]

class Solution2: # bfs queue O(V + E)
    def shortestPathBinaryMatrix(self, grid: List[List[int]]) -> int:
        row_size = len(grid)
        cell_size = len(grid[0])
        if grid[0][0] == 1: return -1
        directions = ((-1,0), (0,-1), (-1,-1), (1,0), (0,1), (1,1), (1,-1), (-1,1))
        distance_matrix = [[-1 for j in range(cell_size)] for i in range(row_size)]
        queue = deque()
        distance_matrix[0][0] = 1
        queue.append((0,0, distance_matrix[0][0]))
        while queue:
            i, j, distance = queue.popleft()
            for di, dj in directions:
                newi = i + di
                newj = j + dj
                if newi >=0 and newi < row_size and newj >= 0 and newj < cell_size and grid[newi][newj]== 0 and (distance_matrix[newi][newj] == -1 or distance_matrix[newi][newj] > distance_matrix[i][j] + 1):
                    distance_matrix[newi][newj] = distance_matrix[i][j] + 1
                    queue.append((newi,newj, distance_matrix[newi][newj]))
        return distance_matrix[row_size - 1][cell_size - 1]