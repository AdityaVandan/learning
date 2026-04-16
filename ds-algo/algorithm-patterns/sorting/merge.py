def merge(input, mid, low, high):
    buffer = [0] * (high - low + 1)

    k = 0
    i, j = low, mid + 1 # j starts at mid + 1

    while i <= mid and j <= high: # both continue till they reach MORE than value of mid and high (stress on <=)
        if input[i] < input[j]:
            buffer[k] = input[i]
            i += 1
        else:
            buffer[k] = input[j]
            j += 1
        k += 1

    while i <= mid:
        buffer[k] = input[i]
        i += 1
        k += 1

    while j <= high:
        buffer[k] = input[j]
        j += 1
        k += 1

    for a in range(k):
        input[low + a] = buffer[a]


def merge_sort(input, low, high):
    if low >= high:
        return

    mid = (low + high) // 2
    merge_sort(input, low, mid)
    merge_sort(input, mid + 1, high)
    merge(input, mid, low, high)


input = [1,5,7,2,8,3,4,9,6,0]
merge_sort(input, 0, len(input)-1)
print(input)