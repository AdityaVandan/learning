from typing import List

class Solution1: # recursive solution with memoization
    def uniquePathsWithObstacles(self, obstacleGrid: List[List[int]]) -> int:
        m = len(obstacleGrid)
        n = len(obstacleGrid[0])
        dp = [[-1]*n for i in range(m)]
        dp[0][0] = 1 if obstacleGrid[0][0] != 1 else 0
        def recursion(m,n):
            if m < 0 or n < 0: return 0
            if dp[m][n] != -1:  return dp[m][n]
            if obstacleGrid[m][n] == 1: dp[m][n] = 0
            else: dp[m][n] = recursion(m-1, n) + recursion(m, n-1)
            return dp[m][n]
        
        return recursion(m - 1, n-1)

class Solution2: # dynamic programming solution
    def uniquePathsWithObstacles(self, obstacleGrid: List[List[int]]) -> int:
        m = len(obstacleGrid)
        n = len(obstacleGrid[0])
        dp = [[-1]*n for i in range(m)]
        found_obstacle = False
        for i in range(m):
            if found_obstacle: dp[i][0] = 0
            elif obstacleGrid[i][0] == 1:
                found_obstacle = True
                dp[i][0] = 0
            else: dp[i][0] = 1

        found_obstacle = False
        for i in range(n):
            if found_obstacle:dp[0][i] = 0
            elif obstacleGrid[0][i] == 1:
                found_obstacle = True
                dp[0][i] = 0
            else: dp[0][i] = 1

        for i in range(1, m):
            for j in range(1, n):
                dp[i][j] = dp[i-1][j] + dp[i][j-1] if obstacleGrid[i][j] != 1 else 0
        
        return dp[m-1][n-1]

class Solution3: # dynamic programming solution (space optimized)
    def uniquePathsWithObstacles(self, obstacleGrid):
        m, n = len(obstacleGrid), len(obstacleGrid[0])

        prev = [0] * n
        curr = [0] * n

        prev[0] = 1 if obstacleGrid[0][0] == 0 else 0

        for j in range(1, n):
            if obstacleGrid[0][j] == 0:
                prev[j] = prev[j - 1]

        for i in range(1, m):
            curr[0] = prev[0] if obstacleGrid[i][0] == 0 else 0

            for j in range(1, n):
                if obstacleGrid[i][j] == 1:
                    curr[j] = 0
                else:
                    curr[j] = prev[j] + curr[j - 1]

            prev, curr = curr, [0] * n

        return prev[-1]