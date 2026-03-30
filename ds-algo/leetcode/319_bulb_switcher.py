class Solution1: # brute force O(NlogN) O(N)
    def bulbSwitch(self, n: int) -> int:
        bulbs = [False]*n
        for i in range(n):
            counter = i+1
            j = counter
            while j <= n:
                bulbs[j-1]=not bulbs[j-1]
                j+=counter
        count = 0
        for i in bulbs:
            if i: count+=1
        return count
    
class Solution2: # O(1) as only perfect squares have odd number of divisors i.e. bulb would be on
    def bulbSwitch(self, n: int) -> int:
        return int(math.sqrt(n) // 1)
