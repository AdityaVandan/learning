class Solution: # O(N)
    def containsCycle(self, grid: List[List[str]]) -> bool:
        stack = []
        grid_size = len(grid)
        row_size = len(grid[0])
        directions = ((-1,0), (0,-1), (1,0), (0,1))
        visited = [[False for cell in row] for row in grid]
        
        for e in range(grid_size):
            for f in range(row_size):
                if visited[e][f]: continue
                visited[e][f] = True
                stack.append((e,f,grid[e][f], -1,-1))
                while len(stack) > 0:
                    i,j,cell,previ,prevj = stack.pop()
                    visited[i][j] = True
                    for direction in directions:
                        newi = i + direction[0]
                        newj = j + direction[1]
                        if newi >=0 and newj >=0 and newi < grid_size and newj < row_size and grid[newi][newj] == cell:
                            if not visited[newi][newj]:
                                visited[newi][newj] = True
                                stack.append((newi,newj, cell, i,j))
                            elif previ != newi or prevj != newj:
                                return True
        
        return False