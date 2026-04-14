class Solution: # dynamic programming O(n)
    def climbStairs(self, n: int) -> int:
        if n == 0: return 0
        if n == 1: return 1
        x = 0
        y = 1
        z = 1
        i = 2
        while i <= n:
            x = y
            y = z
            z = x + y
            i += 1
        
        return z

class Solution2: # recursion
    def climbStairs(self, n: int) -> int:
        if n == 0: return 0
        if n == 1: return 1
        if n == 2: return 2
        return self.climbStairs(n-1) + self.climbStairs(n-2)

class Solution3: # recursion with memoization O(n)
    def climbStairs(self, n: int) -> int:
        cache = [-1]*(n+1)
        cache[0] = 0
        cache[1] = 1
        cache[2] = 2
        return self.recursion(n, cache)

    def recursion(self, n: int, cache: List[int]) -> int:
        if cache[n] != -1: return cache[n]
        cache[n] = self.recursion(n-1, cache) + self.recursion(n-2, cache)
        return cache[n]