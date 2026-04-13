
cache = []
for i in range(100000):
    cache.append(False)

result = []
def all_permutations_of_a_string(input_string: str, buffer: str, input_index: int):
    if input_index >= len(input_string):
        result.append(buffer)
        return
    for index, char in enumerate(input_string):
        if cache[index]:
            continue
        cache[index] = True
        all_permutations_of_a_string(input_string, buffer+char, input_index+1)
        cache[index] = False


input = "aditya"
all_permutations_of_a_string(input,'', 0)
print(result)