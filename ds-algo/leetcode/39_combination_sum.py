class Solution:
    def recursion(self, candidates, target, index, current, total, result):
        if total > target:
            return
        if total == target:
            result.append(current[:])
        
        for i in range(index,len(candidates)):
            current.append(candidates[i])
            self.recursion(candidates, target, i, current, total + candidates[i], result)
            current.pop()

    def combinationSum(self, candidates: List[int], target: int) -> List[List[int]]:
        result = []
        self.recursion(candidates, target, 0, [], 0, result)
        return result