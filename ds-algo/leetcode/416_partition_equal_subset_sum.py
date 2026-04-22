from typing import List

class Solution1: # recursive solution with memoization
    def canPartition(self, nums: List[int]) -> bool:
        total = 0
        n = len(nums)
        for i in range(n): total+=nums[i]
        if total % 2 == 1: return False
        target = total // 2
        dp = [[-1]*(target+1) for i in range(n)]
        def recursion(n, target):
            if target < 0: return False
            if n == 0: return target == 0
            if dp[n][target] != -1: return dp[n][target]
            dp[n][target] = recursion(n-1, target - nums[n]) or recursion(n-1, target)
            return dp[n][target]
        
        return recursion(n-1, target)

class Solution2: # dp solution
    def canPartition(self, nums: List[int]) -> bool:
        total = 0
        n = len(nums)
        for i in range(n): total+=nums[i]
        if total % 2 == 1: return False
        target = total // 2
        dp = [[-1]*(target+1) for i in range(n)]
        for i in range(n): dp[i][0] = True
        dp[0][0] = True
        for i in range(n):
            for j in range(target+1):
                if j - nums[i] >= 0:
                    pick = dp[i-1][j - nums[i]] if dp[i-1][j - nums[i]] != -1 else False
                else: pick = False
                not_pick = dp[i-1][j] if dp[i-1][j] != -1 else False 
                dp[i][j] = pick or not_pick
        return dp[n-1][target] if dp[n-1][target] != -1 else False


class Solution3: # dp solution with space optimization
    def canPartition(self, nums: List[int]) -> bool:
        total = 0
        n = len(nums)
        for i in range(n): total+=nums[i]
        if total % 2 == 1: return False
        target = total // 2
        dp = [[-1]*(target+1) for i in range(2)]
        for i in range(2): dp[i][0] = True
        for i in range(n):
            for j in range(target+1):
                if j - nums[i] >= 0:
                    pick = dp[0][j - nums[i]] if dp[0][j - nums[i]] != -1 else False
                else: pick = False
                not_pick = dp[0][j] if dp[0][j] != -1 else False 
                dp[1][j] = pick or not_pick
            dp[1],dp[0] = dp[0],dp[1]
        return dp[0][target] if dp[0][target] != -1 else False
