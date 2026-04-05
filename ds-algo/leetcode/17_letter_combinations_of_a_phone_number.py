from typing import List


class Solution:
    def __init__(self):
        self.cache = {
            "2": "abc",
            "3": "def",
            "4": "ghi",
            "5": "jkl",
            "6": "mno",
            "7": "pqrs",
            "8": "tuv",
            "9": "wxyz"
        }
    def letterCombinations(self, digits: str) -> List[str]:
        result = []
        for digit in digits:
            characters = self.cache[digit]
            current=[val for val in result]
            if len(current) == 0: result = [character for character in characters]
            else:
                newResult = []
                for character in characters:
                    for val in current:
                        newResult.append(val+character)
                result = newResult
        
        return result
