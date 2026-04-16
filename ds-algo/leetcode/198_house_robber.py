from typing import List

class Solution1: # recursive solution with memoization
    def rob(self, nums: List[int]) -> int:
        def f(n):
            if n<0: return 0

            pick = nums[n] + f(n-2)
            not_pick = 0 + f(n-1)

            return max(pick, not_pick)
        
        return f(len(nums)-1)

class Solution2: # recursive solution with memoization (choosing not choosing)
    def rob(self, nums: List[int]) -> int:
        dp = {}
        def f(n):
            if n<0: return 0
            value = dp.get(n,None)
            if value is not None: return value

            pick = nums[n] + f(n-2)
            not_pick = 0 + f(n-1)
            dp[n] = max(pick, not_pick)
            return dp[n]
        
        return f(len(nums)-1)

class Solution3: # dynamic programming solution (dp array)
    def rob(self, nums: List[int]) -> int:
        n = len(nums)
        if n == 0: return 0
        if n == 1: return nums[0]

        dp = [-1]*n
        dp[0] = nums[0]

        dp[1] = max(nums[0], nums[1])
        for i in range(2,n):
            chosen = nums[i] + dp[i-2]
            not_chosen = dp[i-1]
            dp[i] = max(chosen, not_chosen)
        
        return dp[n-1]

class Solution4: # dynamic programming solution (space optimized)
    def rob(self, nums: List[int]) -> int:
        if len(nums) == 0: return 0
        if len(nums) == 1: return nums[0]

        prev = nums[0]
        prev2 = 0

        for i in range(1,len(nums)):
            chosen = nums[i]
            if i > 1: chosen += prev2
            not_chosen = 0 + prev
            prev2 = prev
            prev = max(not_chosen, chosen)
        
        return prev
