from typing import List


class Solution:
    def recursion(self, candidates: List[int], target: int, start: int, current_result: List[int], result: List[List[int]]):
        if target < 0: return
        if target == 0:
            print(current_result, start)
            result.append(current_result[:])
            return
        for i in range(start, len(candidates)):
            if i > start and candidates[i] == candidates[i - 1]:
                continue
            if candidates[i] > target:
                break
            current_result.append(candidates[i])
            self.recursion(candidates, target - candidates[i], i + 1, current_result, result)
            current_result.pop()
    def combinationSum2(self, candidates: List[int], target: int) -> List[List[int]]:
        result = []
        input_candidates = candidates[:]
        input_candidates.sort()
        self.recursion(input_candidates, target, 0, [],result)
        return result