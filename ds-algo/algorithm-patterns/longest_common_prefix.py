from typing import List
def longestCommonPrefix(strs: List[str]) -> str:
    if len(strs) == 0:
        return ""
    cache = strs[0]+ ""
    total_strings = len(strs)
    for index in range(1, total_strings):
        i = 0
        new_cache = ""
        string_length = len(strs[index])
        cache_length = len(cache)
        while i < string_length:
            if i>=cache_length or cache[i] != strs[index][i]:
                break
            new_cache = new_cache + cache[i]
            i += 1
        cache = new_cache
    
    return cache

input = ["flower","flow","flight"]
result = longestCommonPrefix(input)
print(result)