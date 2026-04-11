class Solution: # bfs queue O(V + E)
    def findLadders(self, beginWord: str, endWord: str, wordList: List[str]) -> List[List[str]]:
        word_set = set(wordList)
        if endWord not in word_set: return []
        queue = deque()
        queue.append((beginWord, [beginWord]))
        word_length = len(beginWord)
        word_paths = []
        found = False
        while queue and not found:
            level_size = len(queue)
            used_words = set()
            for _ in range(level_size):
                word, word_path = queue.popleft()
                for i in range(word_length):
                    for letter in 'abcdefghijklmnopqrstuvwxyz':
                        new_word = f"{word[:i]}{letter}{word[i+1:]}"
                        if new_word in word_set:
                            # word_set.remove(new_word)
                            new_word_path = list(word_path)
                            new_word_path.append(new_word)
                            used_words.add(new_word)
                            if new_word == endWord:
                                found = True
                                word_paths.append(new_word_path)
                            else: queue.append((new_word, new_word_path))
            word_set -= used_words
        return word_paths
