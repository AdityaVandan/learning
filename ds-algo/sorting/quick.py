def quick_partition(input, low, high):
    print("start", input)
    pivot = input[high]
    i = low
    for j in range(low, high): # stops before high
        print("between", input, i,j)
        if pivot > input[j]:
            input[i], input[j] = input[j], input[i] 
            i+=1
    input[high], input[i] = input[i],input[high]

    print('end',input, high, pivot)
    return i

def quick_sort(input, low, high):
    if low >= high:
        return

    partition = quick_partition(input, low, high)
    quick_sort(input, low, partition - 1)
    quick_sort(input, partition + 1, high) 
    return


input = [1,5,7,2,8,3,4,9,6]
quick_sort(input, 0, len(input)-1)
print(input)