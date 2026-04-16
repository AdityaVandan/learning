## Solution 1: Recursive solution with memoization
def recursion(nums,n, cache): # recursive solution with memoization
    if n < 0: return 0
    value = cache.get(n, None)
    if value is not None: return value

    max_sum = 0
    for j in range(n,-1, -1):
        iterative_sum = 0
        for i in range(2,j+1): iterative_sum = max(iterative_sum,recursion(nums,j-i, cache))
        num_sum = nums[j] + iterative_sum
        max_sum = max(num_sum, max_sum)
    cache[n] = max_sum
    return max_sum


def maximumNonAdjacentSum(nums):    
    # Write your code here.
    cache = {}
    output = recursion(nums, len(nums)-1, cache)
    return output

## Solution 2: Recursive solution with memoization (choosing not choosing)
def f(nums, n, dp):
    if n < 0: return 0
    chosen = nums[n] + f(nums, n-2, dp)
    not_chosen = 0 + f(nums, n-1,dp)

    return max(chosen, not_chosen)

def maximumNonAdjacentSum(nums):    
    # Write your code here.
    dp = {}
    return f(nums, len(nums)-1, dp)


## Solution 3: Dynamic programming solution (dp array)
def maximumNonAdjacentSum(nums):
    # Write your code here.
    if not nums:
        return 0
    if len(nums) == 1:
        return nums[0]

    dp = [0] * len(nums)
    dp[0] = nums[0]
    dp[1] = max(nums[0], nums[1])

    for i in range(2, len(nums)):
        chosen = nums[i] + dp[i - 2]
        not_chosen = dp[i - 1]
        dp[i] = max(chosen, not_chosen)

    return dp[-1]



## Solution 4: Dynamic programming solution
def maximumNonAdjacentSum(nums):    
    # Write your code here.
    current = nums[0]
    previous = 0
    chosen = 0
    not_chosen = 0
    max_sum = 0
    for i in range(1, len(nums)):
        chosen = nums[i]
        if (i > 1): chosen += previous
        not_chosen = 0 + current
        max_sum = max(chosen, not_chosen)
        previous = current
        current = max_sum
    return current
