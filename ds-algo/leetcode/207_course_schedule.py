from typing import List
from collections import deque


class Solution1: # kahn's algorithm queue O(V + E)
    def canFinish(self, numCourses: int, prerequisites: List[List[int]]) -> bool:
        indegrees = [0]*numCourses
        graph = [[] for i in range(numCourses)]
        for course, prerequisite_course in prerequisites:
            graph[prerequisite_course].append(course)
            indegrees[course] += 1

        queue = deque([course for course in range(numCourses) if indegrees[course] == 0])
        
        finishable_course_count = 0
        while queue:
            course = queue.popleft()
            finishable_course_count += 1
            for next_course in graph[course]:
                indegrees[next_course] -= 1
                if indegrees[next_course] == 0: queue.append(next_course)
        
        return finishable_course_count == numCourses


class Solution2:  # DFS three-color (WHITE/GRAY/BLACK) O(V + E)
    """GRAY neighbor = back edge = directed cycle."""

    def canFinish(self, numCourses: int, prerequisites: List[List[int]]) -> bool:
        graph = [[] for _ in range(numCourses)]
        for course, prerequisite_course in prerequisites:
            graph[prerequisite_course].append(course)

        WHITE, GRAY, BLACK = 0, 1, 2
        color = [WHITE] * numCourses

        def dfs(u: int) -> bool:
            color[u] = GRAY
            for v in graph[u]:
                if color[v] == GRAY:
                    return False
                if color[v] == WHITE and not dfs(v):
                    return False
            color[u] = BLACK
            return True

        for i in range(numCourses):
            if color[i] == WHITE and not dfs(i):
                return False
        return True


class Solution3:  # DFS visited + recursion stack O(V + E)
    """Same idea as ds-algo/graph/cycle_in_a_directed_graph.py Solution1."""

    def canFinish(self, numCourses: int, prerequisites: List[List[int]]) -> bool:
        graph = [[] for _ in range(numCourses)]
        for course, prerequisite_course in prerequisites:
            graph[prerequisite_course].append(course)

        visited = [False] * numCourses
        on_stack = [False] * numCourses

        def dfs(u: int) -> bool:
            visited[u] = True
            on_stack[u] = True
            for v in graph[u]:
                if not visited[v]:
                    if dfs(v):
                        return True
                elif on_stack[v]:
                    return True
            on_stack[u] = False
            return False

        for i in range(numCourses):
            if not visited[i] and dfs(i):
                return False
        return True

