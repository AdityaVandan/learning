output = []
def make_combination(inputs, index = 0, buffer = []):
    if index >= len(inputs):
        output.append([i for i in buffer])
        return

    for input_list_index in range(len(inputs[index])):
        buffer.append(inputs[index][input_list_index])
        make_combination(inputs, index + 1, buffer)
        buffer.pop()
        
    return


testcase = [["a","b","c"], ["+","-", "*","/"], ["1","2"]]

make_combination(testcase)
for o in output:
    print(o)