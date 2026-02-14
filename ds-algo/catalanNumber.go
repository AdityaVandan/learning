// package main

import "fmt"

var cache []uint64

func CalculateCatalanNumber(n uint64) uint64 {
	var totalSum uint64 = 0
	if n < 0 {
		return 1
	}
	if cache[n] != 0 {
		return cache[n]
	}
	var i uint64 = 0
	for i = 0; i < n; i++ {
		currentCatalanNumber := CalculateCatalanNumber(i) * CalculateCatalanNumber(n-i-1)
		totalSum += currentCatalanNumber
	}
	cache[n] = totalSum

	return cache[n]
}

func GetCatalanNumber(n uint64) uint64 {
	cache = make([]uint64, n+1)
	for i := 0; i < len(cache); i++ {
		cache[i] = 0
	}
	cache[0] = 1
	return CalculateCatalanNumber(n)
}

func main() {
	var n uint64 = 100
	var i uint64
	for i = 0; i < n; i++ {
		result := GetCatalanNumber(i)
		fmt.Println(i, result)
	}
}
