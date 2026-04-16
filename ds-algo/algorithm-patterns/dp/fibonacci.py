# top down
cache = [-1]*10
cache[0] = 0
cache[1] = 1
def fibonacci(n):
    if cache[n] == -1:
        cache[n] = fibonacci(n-1) + fibonacci(n-2)
    
    return cache[n]

print(fibonacci(0))
print(fibonacci(1))
print(fibonacci(2))
print(fibonacci(3))
print(fibonacci(4))
print(fibonacci(5))
print(fibonacci(6))
print(fibonacci(7))
print(fibonacci(8))
print(fibonacci(9))

# bottom up
def fibonacci2(n):
    x = 0
    y = 1
    for i in range(n):
        z = x + y
        print(z)
        x = y
        y = z

print('next')
fibonacci2(9)