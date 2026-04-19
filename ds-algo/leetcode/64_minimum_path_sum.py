class Solution1: # recursive solution with memoization
    def minPathSum(self, grid):
        rows, cols = len(grid), len(grid[0])

        dp = [[-1] * cols for _ in range(rows)]
        INF = float('inf')

        def dfs(i, j):
            if i < 0 or j < 0:
                return INF

            if i == 0 and j == 0:
                return grid[0][0]

            if dp[i][j] != -1:
                return dp[i][j]

            dp[i][j] = grid[i][j] + min(
                dfs(i - 1, j),
                dfs(i, j - 1)
            )

            return dp[i][j]

        return dfs(rows - 1, cols - 1)

class Solution2: # dynamic programming solution
    def minPathSum(self, grid):
        m, n = len(grid), len(grid[0])

        dp = [[-1] * n for _ in range(m)]
        dp[0][0] = grid[0][0]
        for i in range(1,m): dp[i][0] = dp[i-1][0] + grid[i][0]
        for i in range(1,n): dp[0][i] = dp[0][i-1] + grid[0][i]

        for i in range(1,m):
            for j in range(1,n):
                dp[i][j] = min(dp[i-1][j], dp[i][j-1]) + grid[i][j]
        
        return dp[m-1][n-1]


class Solution3: # dynamic programming solution (space optimized)
    def minPathSum(self, grid):
        m, n = len(grid), len(grid[0])

        dp = [[-1] * n for _ in range(2)]
        dp[0][0] = grid[0][0]
        for i in range(1,n): dp[0][i] = dp[0][i-1] + grid[0][i]

        for i in range(1,m):
            dp[1][0] = dp[0][0] + grid[i][0]
            for j in range(1,n):
                dp[1][j] = min(dp[0][j], dp[1][j-1]) + grid[i][j]
            dp.reverse()
        
        return dp[0][n-1]


