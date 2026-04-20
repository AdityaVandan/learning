from typing import List
class Solution1: # recursive solution with memoization
    def findTargetSumWays(self, nums: List[int], target: int) -> int:
        total = 0
        for i in range((len(nums))): total+= nums[i]
        dp = {}
        def recursion(n, target):
            if n < 0: return 0
            if n == 0:
                count = 0
                if target + nums[n] == 0: count += 1
                if target - nums[n] == 0: count += 1
                return count
            if dp.get((n, target), None) is not None: return dp[(n, target)]
            dp[(n, target)] = recursion(n-1, target - nums[n]) + recursion(n-1, target + nums[n])
            return dp[(n, target)]

        
        return recursion(len(nums)-1, target)

class Solution2: # dp solution with space optimization
    def findTargetSumWays(self, nums: List[int], target: int) -> int:
        dp = [[-1]*(3000) for i in range(len(nums))]
        def recursion(n, target):
            if n < 0: return 0
            if n == 0:
                count = 0
                if target + nums[n] == 0: count += 1
                if target - nums[n] == 0: count += 1
                return count
            target_key = 1000 + target if target > 0 else abs(target)
            if dp[n][target_key] != -1: return dp[n][target_key]
            dp[n][target_key] = recursion(n-1, target - nums[n]) + recursion(n-1, target + nums[n])
            return dp[n][target_key]

        
        return recursion(len(nums)-1, target)

# TODO: dp + space optimization