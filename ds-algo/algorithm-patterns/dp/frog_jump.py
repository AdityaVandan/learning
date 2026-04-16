def f(n, height): # recursive solution
    if n <= 1: return 0
    if n == 2: return abs(height[1] - height[0])
    return min(f(n-1)+abs(height[n-1] - height[n-2]), f(n-2)+abs(height[n-1] - height[n-3]))
          

def minCost(height): # recursive solution with memoization
    # code here
    if len(height) <= 1: return 0
    jump_cache = [-1]*(len(height) + 1)
    jump_cache[0] = jump_cache[1] = 0
    jump_cache[2] = abs(height[1] - height[0])
    def f(n):
        if jump_cache[n] != -1: return jump_cache[n]
        jump_cache[n] = min(f(n-1)+abs(height[n-1] - height[n-2]), f(n-2)+abs(height[n-1] - height[n-3]))
        return jump_cache[n]
    
    return f(len(height))



class Solution: # dynamic programming solution
    def minCost(self, height):
        # code here
        if len(height) <= 1: return 0
        n = len(height)
        jump_cache = [-1]*n
        jump_cache[0] = 0
        jump_cache[1] = abs(height[0] - height[1])
        i = 1
        while i < n - 1:
            i += 1
            jump_cache[i] = min(jump_cache[i-1] + abs(height[i-1] - height[i]), jump_cache[i-2] + abs(height[i-2] - height[i]))
        
        return jump_cache[n-1]
            
