class Solution:
    def orangesRotting(self, grid: List[List[int]]) -> int:
        queue = deque()
        grid_size = len(grid)
        row_size = len(grid[0])
        directions = ((0,-1), (-1,0), (0,1), (1,0))

        for i in range(grid_size):
            for j in range(row_size):
                if grid[i][j] == 2: queue.append((i,j, 0))
        
        time_counter = 0
        while len(queue) > 0:
            nodei, nodej, counter = queue.popleft()
            for direction in directions:
                newi = nodei + direction[0]
                newj = nodej + direction[1]
                time_counter = max(counter, time_counter)
                if newi >= 0 and newi < grid_size and newj >= 0 and newj < row_size and grid[newi][newj] == 1:
                    grid[newi][newj] = 2
                    queue.append((newi, newj, counter + 1))
        print(grid)
        print(time_counter)

        for i in range(grid_size):
            for j in range(row_size):
                if grid[i][j] == 1: return -1

        return time_counter
