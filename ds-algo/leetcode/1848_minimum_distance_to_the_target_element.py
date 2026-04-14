from typing import List
class Solution:
    def getMinDistance(self, nums: List[int], target: int, start: int) -> int:
        list_length = len(nums)
        i=start
        j=start
        while i >=0 or j < list_length:
            if i >= 0:
                if nums[i] != target: i -= 1
                else: return abs(start - i)
            if j < list_length: 
                if nums[j] != target: j += 1
                else: return abs(start - j)
        return -1