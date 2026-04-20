from typing import List

class Solution1: # recursive solution with memoization
    def cherryPickup(self, grid: List[List[int]]) -> int:
        m = len(grid)
        n = len(grid[0])
        directions = (-1,0,1)
        grid.reverse()
        dp = [[[-1]*n for i in range(n)] for j in range(m)]
        def recursion(m,i,k):
            if m < 0 or i < 0 or i >= n or k < 0 or k >= n or i == k: return -100000
            if m == 0: return grid[m][i] + grid[m][k]
            if dp[m][i][k] != -1: return dp[m][i][k]
            max_cherries = -100000
            for direction1 in directions:
                for direction2 in directions:
                    max_cherries = max(max_cherries, grid[m][i] + grid[m][k] + recursion(m-1, i+direction1,k+direction2))
            dp[m][i][k] = max_cherries
            return dp[m][i][k]
        return recursion(m-1,0, n-1)
            
# TODO: dp + space optimization