import heapq
from typing import List

class Solution: # dijkstra heap O(V log V + E log V)
    def minimumEffortPath(self, heights: List[List[int]]) -> int:
        row_size = len(heights)
        cell_size = len(heights[0])
        directions = ((-1,0), (0,-1), (1,0), (0,1))
        distance_matrix = [[-1 for j in range(cell_size)] for i in range(row_size)]
        queue = []
        distance_matrix[0][0] = 0
        heapq.heappush(queue, (distance_matrix[0][0], (0,0)))
        # print(distance_matrix)

        while queue:
            prev_max_diff, node = heapq.heappop(queue)
            i, j = node
            for di, dj in directions:
                newi = i + di
                newj = j + dj
                if newi >=0 and newi < row_size and newj >= 0 and newj < cell_size:
                    max_diff = max(prev_max_diff, abs(heights[newi][newj] - heights[i][j]))
                    if distance_matrix[newi][newj] == -1 or distance_matrix[newi][newj] > max_diff:
                        distance_matrix[newi][newj] = max_diff
                        heapq.heappush(queue, (distance_matrix[newi][newj], (newi,newj)))
        # print(distance_matrix)
        return distance_matrix[row_size - 1][cell_size - 1]
