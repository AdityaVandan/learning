class Solution1: # brute force O(N*M)
    def strStr(self, haystack: str, needle: str) -> int:
        i = 0
        haystack_length = len(haystack)
        needle_length = len(needle)
        found = None
        result = -1
        while i in range(haystack_length):
            if i+needle_length > haystack_length: break
            j = 0
            found = True
            while j in range(needle_length):
                if haystack[i + j] != needle[j]:
                    # print(i, j)
                    found = False
                    break
                j+=1
            # print(haystack[i], i, found)
            if found:
                result = i
                break
            i+=1
        
        return result

