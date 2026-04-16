def bubble(input):
    result = [i for i in input]
    for i in range(len(result)):
        minValIndex = i
        for j in range(i, len(result)):
            minValIndex = j if result[j] < result[minValIndex] else minValIndex
        minVal = result[minValIndex]
        result[minValIndex] = result[i]
        result[i] = minVal
    return result


input = [1,5,7,2,8,3,4,9,6,0]
print("Input: ",input)

result = bubble(input)
print("bubble: ",result)

input.sort()
print("builtin sort",input)
