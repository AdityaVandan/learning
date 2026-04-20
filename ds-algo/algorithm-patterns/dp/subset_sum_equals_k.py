class Solution1: # recursive solution with memoization
    def isSubsetSum (self, arr, sum):
        # code here 
        n = len(arr)
        dp = [[-1]*(sum+1) for i in arr]
        def recursion(n, target):
            if target < 0: return False
            if n < 0: return target == 0
            if dp[n][target] != -1: return dp[n][target]
            pick = recursion(n-1, target - arr[n])
            not_pick = recursion(n-1, target)
            dp[n][target] = pick or not_pick
            return dp[n][target]

        return recursion(len(arr) - 1, sum)

class Solution2: # dp solution with space optimization
    def isSubsetSum (self, arr, sum):
        # code here 
        n = len(arr)
        dp = [[False]*(sum+1) for i in arr]
        for i in range(n): dp[i][0] = True
        if arr[0] <= sum: dp[0][arr[0]] = True
        for i in range(1,n):
            for j in range(sum+1):
                pick = dp[i-1][j-arr[i]] if j-arr[i] >=0 else False
                dp[i][j] = dp[i-1][j] or pick

        return dp[len(arr)-1][sum]

class Solution3: # dp solution with space optimization
    def isSubsetSum (self, arr, sum):
        # code here 
        n = len(arr)
        dp = [[False]*(sum+1) for i in range(2)]
        for i in range(2): dp[i][0] = True
        if arr[0] <= sum: dp[0][arr[0]] = True
        for i in range(1,n):
            for j in range(sum+1):
                pick = dp[0][j-arr[i]] if j-arr[i] >=0 else False
                dp[1][j] = dp[0][j] or pick
            dp[0],dp[1] = dp[1],dp[0]

        return dp[0][sum]
