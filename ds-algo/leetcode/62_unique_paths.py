class Solution1: # recursive solution with memoization
    def recursion(self, m: int, n:int, cache: any):
        if m < 0 or n < 0: return 0
        if cache[m][n] != -1: return cache[m][n]
        cache[m][n] = self.recursion(m, n-1, cache) + self.recursion(m-1, n, cache)
        return cache[m][n]
    def uniquePaths(self, m: int, n: int) -> int:
        cache = [[-1]*n for i in range(m)]
        cache[0][0] = 1
        return self.recursion(m-1,n-1, cache)

class Solution2: # dynamic programming solution
    def uniquePaths(self, m: int, n: int) -> int:
        cache = [[-1]*n for i in range(m)]
        for i in range(m): cache[i][0] = 1
        for j in range(n): cache[0][j] = 1
        for i in range(1,m):
            for j in range(1,n):
                cache[i][j] = cache[i-1][j] + cache[i][j-1]
        return cache[m-1][n-1]