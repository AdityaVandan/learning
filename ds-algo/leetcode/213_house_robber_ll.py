from typing import List

class Solution1: # recursive solution with memoization
    def rob(self, nums: List[int]) -> int:
        if len(nums) == 0: return 0
        if len(nums) == 1: return nums[0]
        cache1 = [-1]*(len(nums) - 1)
        num_list1 = nums[:len(nums) - 1]
        cache2 = [-1]*(len(nums) - 1)
        num_list2 = nums[1:]
        def f(n, num_list, dp):
            if n < 0: return 0
            if dp[n] != -1: return dp[n]
            pick = num_list[n] + f(n-2, num_list, dp)
            not_pick = 0 + f(n-1, num_list, dp)
            dp[n] = max(pick, not_pick)
            return dp[n]
        return max(f(len(num_list1)-1, num_list1, cache1), f(len(num_list2)-1, num_list2, cache2))


class Solution2:  # bottom-up dp
    def rob(self, nums: List[int]) -> int:
        if len(nums) == 0:
            return 0
        if len(nums) == 1:
            return nums[0]

        def linear_rob(arr: List[int]) -> int:
            n = len(arr)
            if n == 0:
                return 0
            if n == 1:
                return arr[0]
            dp = [0] * n
            dp[0] = arr[0]
            dp[1] = max(arr[0], arr[1])
            for i in range(2, n):
                dp[i] = max(dp[i - 1], arr[i] + dp[i - 2])
            return dp[n - 1]

        return max(linear_rob(nums[:-1]), linear_rob(nums[1:]))


class Solution3:  # space optimised: O(1) linear rob with two rolling values
    def rob(self, nums: List[int]) -> int:
        if len(nums) == 0:
            return 0
        if len(nums) == 1:
            return nums[0]

        def linear_rob(arr: List[int]) -> int:
            prev2, prev1 = 0, 0
            for x in arr:
                prev2, prev1 = prev1, max(prev1, prev2 + x)
            return prev1

        return max(linear_rob(nums[:-1]), linear_rob(nums[1:]))
