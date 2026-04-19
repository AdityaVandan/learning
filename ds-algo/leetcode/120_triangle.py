from typing import List

class Solution1: # recursive solution with memoization
    def minimumTotal(self, triangle: List[List[int]]) -> int:
        upward_triangle = triangle
        upward_triangle.reverse()
        m = len(upward_triangle)
        n = len(upward_triangle[0])
        dp = [[None for j in range(n)] for i in range(m)]
        for i in range(n): dp[0][i] = upward_triangle[0][i]

        def recursion(m,n):
            if m < 0 or n >= len(upward_triangle[m]) or n < 0: return 100000
            if dp[m][n] != None: return dp[m][n]
            dp[m][n] = upward_triangle[m][n] + min(recursion(m-1,n), recursion(m-1, n+1))
            return dp[m][n]
        min_total = recursion(m-1, 0)
        
        return min_total

class Solution2: # dynamic programming solution
    def minimumTotal(self, triangle: List[List[int]]) -> int:
        m = len(triangle)
        n = len(triangle[m-1])
        dp = [[100000 for j in range(n)] for i in range(m)]
        dp[0][0] = triangle[0][0]
        for i in range(1,m): dp[i][0] = triangle[i][0] + dp[i-1][0]

        for i in range(m):
            for j in range(1,i+1):
                dp[i][j] = triangle[i][j] + min(dp[i-1][j],dp[i-1][j-1])
        min_total = 100000
        for i in range(n): min_total = min(dp[m-1][i], min_total)
        return min_total

class Solution3: # dynamic programming solution (space optimized)
    def minimumTotal(self, triangle: List[List[int]]) -> int:
        m = len(triangle)
        n = len(triangle[m-1])
        dp = [[100000 for j in range(n)] for i in range(2)]
        dp[0][0] = triangle[0][0]

        for i in range(1,m):
            for j in range(i+1):
                dp[1][j] = triangle[i][j] + min(dp[0][j],dp[0][j-1])
            dp[1], dp[0] = dp[0], dp[1]
        min_total = 100000
        for i in range(n): min_total = min(dp[0][i], min_total)
        return min_total