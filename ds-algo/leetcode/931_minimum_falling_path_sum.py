from typing import List

class Solution1: # recursive solution with memoization
    def minFallingPathSum(self, matrix: List[List[int]]) -> int:
        cols, rows = len(matrix), len(matrix[0])
        dp = [[100000]*rows for i in range(cols)]
        def recursion(m,n):
            if m < 0 or n < 0 or n >= rows: return 100000
            if m == 0: return matrix[m][n]
            if dp[m][n] != 100000: return dp[m][n]
            dp[m][n] = matrix[m][n] + min(recursion(m-1, n-1), recursion(m-1,n), recursion(m-1, n+1))
            return dp[m][n]
        
        min_total = 100000
        for i in range(rows):
            min_total = min(min_total, recursion(cols-1,i))
        return min_total

class Solution2: # dynamic programming solution
    def minFallingPathSum(self, matrix: List[List[int]]) -> int:
        cols, rows = len(matrix), len(matrix[0])
        dp = [[100000]*rows for i in range(cols)]
        for i in range(rows): dp[0][i] = matrix[0][i]

        for i in range(1,cols):
            for j in range(0,rows):
                left = dp[i-1][j-1] if j-1 >=0 else 100000
                right = dp[i-1][j+1] if j+1 < rows else 100000
                dp[i][j] = matrix[i][j] + min(left, dp[i-1][j], right)

        
        min_total = 100000
        for i in range(rows):
            min_total = min(min_total, dp[cols-1][i])
        return min_total

class Solution3: # dynamic programming solution (space optimized)
    def minFallingPathSum(self, matrix: List[List[int]]) -> int:
        cols, rows = len(matrix), len(matrix[0])
        dp = [[100000]*rows for i in range(2)]
        for i in range(rows): dp[0][i] = matrix[0][i]

        for i in range(1,cols):
            for j in range(0,rows):
                left = dp[0][j-1] if j-1 >=0 else 100000
                right = dp[0][j+1] if j+1 < rows else 100000
                dp[1][j] = matrix[i][j] + min(left, dp[0][j], right)
            dp[1], dp[0] = dp[0], dp[1]

        
        min_total = 100000
        for i in range(rows):
            min_total = min(min_total, dp[0][i])
        return min_total