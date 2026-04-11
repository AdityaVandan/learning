class Solution1: # bfs queue O(V + E)
    def ladderLength(self, beginWord: str, endWord: str, wordList: List[str]) -> int:
        graph = {}
        distance = {}
        word_ladder_list = [beginWord]
        word_ladder_list.extend(wordList)
        end_word_found = False
        for word in word_ladder_list:
            if endWord == word: end_word_found = True
            graph[word] = []
            distance[word] = -1
        
        if not end_word_found: return 0
        
        def is_neighbour(word1, word2):
            if len(word1) != len(word2): return False
            word_cache = {}
            word_length = len(word1)
            count = 0
            for i in range(word_length):
                if word1[i] != word2[i]: count += 1
            return count == 1

        for i in range(len(word_ladder_list)):
            for j in range(i+1,len(word_ladder_list)):
                # print(i,j)
                if is_neighbour(word_ladder_list[i], word_ladder_list[j]):
                    graph[word_ladder_list[i]].append(word_ladder_list[j])
                    graph[word_ladder_list[j]].append(word_ladder_list[i])
        
        queue = deque()
        queue.append(beginWord)
        distance[beginWord] = 1
        # print(distance, queue, graph)
        while queue:
            word = queue.popleft()
            for next_word in graph[word]:
                if distance[next_word] == -1 or distance[next_word] > distance[word] + 1:
                    distance[next_word] = distance[word] + 1
                    queue.append(next_word)
        # print(distance)
        return 0 if distance[endWord] == -1 else distance[endWord]


class Solution2: # bfs queue O(V + E) optimized
    def ladderLength(self, beginWord: str, endWord: str, wordList: List[str]) -> int:
        word_set = set(wordList)
        
        if endWord not in word_set:
            return 0
        
        queue = deque([(beginWord, 1)])
        
        while queue:
            word, level = queue.popleft()
            
            for i in range(len(word)):
                for ch in 'abcdefghijklmnopqrstuvwxyz':
                    new_word = word[:i] + ch + word[i+1:]
                    
                    if new_word == endWord:
                        return level + 1
                    
                    if new_word in word_set:
                        word_set.remove(new_word)
                        queue.append((new_word, level + 1))
        
        return 0