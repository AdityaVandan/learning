class Solution1:  # recursive (no memo)
    @staticmethod
    def get_max_points(matrix):
        def f(n, x):
            if n < 0:
                return 0

            ans = 0
            for i in range(3):
                if i == x:
                    continue
                ans = max(ans, matrix[n][i] + f(n - 1, i))
            return ans

        return f(len(matrix) - 1, -1)


class Solution2:  # top-down with explicit cache
    @staticmethod
    def get_max_points(matrix):
        cache = {}

        def f(n, x):
            if n < 0:
                return 0
            key = (n, x)
            if key in cache:
                return cache[key]

            ans = 0
            for i in range(3):
                if i == x:
                    continue
                ans = max(ans, matrix[n][i] + f(n - 1, i))
            cache[key] = ans
            return ans

        return f(len(matrix) - 1, -1)


class Solution3:  # bottom-up DP: full table
    @staticmethod
    def get_max_points(matrix):
        n = len(matrix)
        if n == 0:
            return 0

        # dp[i][t] = max points up to day i if task t is chosen on day i
        dp = [[0] * 3 for _ in range(n)]
        for t in range(3):
            dp[0][t] = matrix[0][t]

        for i in range(1, n):
            for t in range(3):
                dp[i][t] = matrix[i][t] + max(dp[i - 1][j] for j in range(3) if j != t)

        return max(dp[n - 1])


class Solution4:  # bottom-up, O(1) extra space (only previous day)
    @staticmethod
    def get_max_points(matrix):
        n = len(matrix)
        if n == 0:
            return 0

        prev = [matrix[0][t] for t in range(3)]
        for i in range(1, n):
            curr = [0] * 3
            for t in range(3):
                curr[t] = matrix[i][t] + max(prev[j] for j in range(3) if j != t)
            prev = curr

        return max(prev)
