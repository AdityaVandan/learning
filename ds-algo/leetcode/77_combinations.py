from typing import List


class Solution:
    def recursion(self, start: int, end: int, k: int, current: List[int], result):
        if len(current) == k:
            copy = current[:]
            result.append(copy)
            return
        for i in range(start, end+1):
            current.append(i)
            self.recursion(i+1, end, k, current, result)
            current.pop()

    def combine(self, n: int, k: int) -> List[List[int]]:
        ans = []
        self.recursion(1, n,k,[],ans)
        return ans