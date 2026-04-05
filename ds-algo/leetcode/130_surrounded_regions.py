from collections import deque
from typing import List


class Solution1: # bfs queue O(R*C)
    def solve(self, board: List[List[str]]) -> None:
        """
        Do not return anything, modify board in-place instead.
        """
        row_size = len(board)
        cell_size = len(board[0])
        visited = [[False for i in range(cell_size)] for j in range(row_size)]
        directions = ((1,0), (0,1), (-1,0), (0,-1))
        queue = deque()

        for i in range(row_size):
            for j in range(cell_size):
                if board[i][j] == 'O' and (i == 0 or i == row_size - 1 or j == 0 or j == cell_size - 1):
                    visited[i][j] = True
                    queue.append((i, j))
        
        while queue:
            i,j = queue.popleft()
            for direction in directions:
                newi = i + direction[0]
                newj = j + direction[1]
                if 0 <= newi < row_size and 0 <= newj < cell_size and board[newi][newj] == 'O' and not visited[newi][newj]:
                    visited[newi][newj] = True
                    queue.append((newi,newj))

        for i in range(row_size):
            for j in range(cell_size):
                if  board[i][j] == 'O' and not visited[i][j]:
                    board[i][j] = 'X'

        return


class Solution2: # dfs stack O(R*C)
    def solve(self, board: List[List[str]]) -> None:
        """
        Do not return anything, modify board in-place instead.
        """
        row_size = len(board)
        cell_size = len(board[0])
        visited = [[False for i in range(cell_size)] for j in range(row_size)]
        directions = ((1,0), (0,1), (-1,0), (0,-1))
        stack = []

        for i in range(row_size):
            for j in range(cell_size):
                if board[i][j] == 'O' and (i == 0 or i == row_size - 1 or j == 0 or j == cell_size - 1):
                    visited[i][j] = True
                    stack.append((i, j))

        while stack:
            i, j = stack.pop()
            for direction in directions:
                newi = i + direction[0]
                newj = j + direction[1]
                if 0 <= newi < row_size and 0 <= newj < cell_size and board[newi][newj] == 'O' and not visited[newi][newj]:
                    visited[newi][newj] = True
                    stack.append((newi, newj))

        for i in range(row_size):
            for j in range(cell_size):
                if board[i][j] == 'O' and not visited[i][j]:
                    board[i][j] = 'X'

        return


class Solution3: # dfs recursive O(R*C)
    def solve(self, board: List[List[str]]) -> None:
        """
        Do not return anything, modify board in-place instead.
        """
        row_size = len(board)
        cell_size = len(board[0])
        visited = [[False for i in range(cell_size)] for j in range(row_size)]
        directions = ((1,0), (0,1), (-1,0), (0,-1))

        def dfs(i: int, j: int) -> None:
            visited[i][j] = True
            for direction in directions:
                newi = i + direction[0]
                newj = j + direction[1]
                if 0 <= newi < row_size and 0 <= newj < cell_size and board[newi][newj] == 'O' and not visited[newi][newj]:
                    dfs(newi, newj)

        for i in range(row_size):
            for j in range(cell_size):
                if board[i][j] == 'O' and (i == 0 or i == row_size - 1 or j == 0 or j == cell_size - 1):
                    if not visited[i][j]:
                        dfs(i, j)

        for i in range(row_size):
            for j in range(cell_size):
                if board[i][j] == 'O' and not visited[i][j]:
                    board[i][j] = 'X'

        return
