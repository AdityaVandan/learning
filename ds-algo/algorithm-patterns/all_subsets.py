# solution 1
def copy_on_set(result_set, character):
    temp_set = []
    for value_list in result_set:
        temp_list = []
        for value in value_list:
           temp_list.append(value)
        temp_list.append(character)
        temp_set.append(temp_list)
    
    result_set.extend(temp_set)

def get_all_subset1(input_set):
    result = [[]]
    for character in input_set:
        copy_on_set(result, character)
    
    return result

# result = get_all_subset1([1,2,3,4])
# print(result)

# solution 2
results = []
def get_all_subset2(input_set, input_index, result_set):
    if input_index >= len(input_set):
        results.append(result_set)
        return
    new_result_set = []
    new_result_set.extend(result_set)
    new_result_set.append(input_set[input_index])
    get_all_subset2(input_set, input_index+1, result_set)
    get_all_subset2(input_set, input_index+1, new_result_set)

get_all_subset2([1,2,3], 0, [])
print(results)
