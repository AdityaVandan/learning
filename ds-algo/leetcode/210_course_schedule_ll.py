from typing import List
from collections import deque


class Solution1: # kahn's algorithm queue O(V + E)
    def findOrder(self, numCourses: int, prerequisites: List[List[int]]) -> List[int]:
        indegrees = [0]*numCourses
        graph = [[] for i in range(numCourses)]

        for course, prerequisite in prerequisites:
            graph[prerequisite].append(course)
            indegrees[course] += 1
        
        ordered_courses = []
        queue = deque()
        for course in range(numCourses):
            if indegrees[course] == 0: queue.append(course)

        while queue:
            course = queue.popleft()
            ordered_courses.append(course)
            for next_course in graph[course]:
                indegrees[next_course] -= 1
                if indegrees[next_course] == 0: queue.append(next_course)

        return ordered_courses if len(ordered_courses) == numCourses else []


class Solution2: # dfs recursion with color cache O(V + E)
    def findOrder(self, numCourses: int, prerequisites: List[List[int]]) -> List[int]:
        graph = [[] for i in range(numCourses)]
        colors = [0]*numCourses
        ordered_courses = []

        for course, prerequisite in prerequisites:
            graph[prerequisite].append(course)
        
        def recursion(node):
            if colors[node] == 2: return False
            colors[node] = 1

            for next_node in graph[node]:
                if colors[next_node] == 1: return True
                elif colors[next_node] == 0:
                    is_cycle = recursion(next_node)
                    if is_cycle: return True

            colors[node] = 2
            ordered_courses.append(node)
            return False

        for course in range(numCourses):
            if colors[course] == 0:
                is_cycle = recursion(course)
                if is_cycle:
                    return []
        
        ordered_courses.reverse()
        return ordered_courses
