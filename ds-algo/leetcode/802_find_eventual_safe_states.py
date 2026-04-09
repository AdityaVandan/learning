from typing import List

class Solution1: # dfs recursion O(V + E)
    def recursion(self, graph, current_node, visited, path_visited, result):
        if visited[current_node]: return path_visited[current_node]
        visited[current_node] = True
        path_visited[current_node] = True

        for node in graph[current_node]:
            if not visited[node]:
                is_cycle = self.recursion(graph, node, visited, path_visited, result)
                if is_cycle: return True
            elif path_visited[node]:
                return True

        path_visited[current_node] = False
        return False

        

    def eventualSafeNodes(self, graph: List[List[int]]) -> List[int]:
        node_count = len(graph)
        visited = [False]*node_count
        path_visited = [False]*node_count
        result = []
        for i in range(node_count):
            is_cycle = self.recursion(graph, i, visited, path_visited,result)
            if not is_cycle:
                result.append(i)
        return result

class Solution2: # dfs recursion with color cache O(V + E)
    def eventualSafeNodes(self, graph: List[List[int]]) -> List[int]:
        node_count = len(graph)
        color_cache = [0]*node_count
        result = []
        def recursion(node):
            if color_cache[node] == 2: return False
            color_cache[node] = 1
            for next_node in graph[node]:
                if color_cache[next_node] == 1: return True
                elif color_cache[next_node] == 0:
                    is_cycle = recursion(next_node)
                    if is_cycle: return True
            color_cache[node] = 2
            return False

        for i in range(node_count):
            is_cycle = recursion(i)
            if not is_cycle:
                result.append(i)
        return result
