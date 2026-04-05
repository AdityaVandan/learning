from typing import List


class Solution1: # recrusion
    def __init__(self):
        self.visited = {}
    def recursion(self, graph: List[List[int]], node):
        self.visited[node] = True
        for i in range(len(graph[node])):
            if graph[node][i] == 1 and not self.visited.get(i, False):
                self.recursion(graph, i)
    def findCircleNum(self, isConnected: List[List[int]]) -> int:
        node_count = len(isConnected)
        if node_count == 0: return 0
        province_count = 0

        for i in range(node_count):
            if self.visited.get(i,False): continue
            province_count += 1
            self.recursion(isConnected, i)
        
        return province_count
    
class Solution2: # stack
    def findCircleNum(self, isConnected: List[List[int]]) -> int:
        node_count = len(isConnected)
        province_count = 0
        visited = [False]*node_count
        stack = []

        for i in range(node_count):
            if visited[i]: continue
            province_count += 1
            stack.append(i)
            while len(stack) > 0:
                node = stack.pop()
                visited[node] = True
                for j in range(node_count):
                    if isConnected[node][j] == 1 and not visited[j]:
                        stack.append(j)
        return province_count