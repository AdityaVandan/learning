package main

import "fmt"

// pivot logic
func getMaxPalindrome(s string, pivotStart int, pivotEnd int) string {
	stringLength := len(s)
	maxPalindromeLength := 0
	var maxPalindrome string = ""
	for i := 0; pivotEnd+i < stringLength && pivotStart-i >= 0; i += 1 {
		if s[pivotEnd+i] != s[pivotStart-i] {
			break
		}
		currentPalindromeLength := 2*i + 1
		if currentPalindromeLength > maxPalindromeLength {
			maxPalindromeLength = currentPalindromeLength
			maxPalindrome = s[pivotStart-i : pivotEnd+i+1]
		}
	}
	return maxPalindrome
}

func FindLongestPalindrome(s string) string {
	stringLength := len(s)
	maxPalindrome := ""
	for i := 0; i < stringLength; i++ {
		maxPalindromeOdd := getMaxPalindrome(s, i, i)
		maxPalindromeEven := getMaxPalindrome(s, i, i+1)
		fmt.Println("debug", i, "maxPalindromeOdd", maxPalindromeOdd, "maxPalindromeEven", maxPalindromeEven)
		if len(maxPalindromeEven) > len(maxPalindromeOdd) && len(maxPalindromeEven) > len(maxPalindrome) {
			maxPalindrome = maxPalindromeEven
		} else if len(maxPalindromeOdd) > len(maxPalindromeEven) && len(maxPalindromeOdd) > len(maxPalindrome) {
			maxPalindrome = maxPalindromeOdd
		}
	}

	return maxPalindrome
}

// dp logic
// TODO

func main() {
	result := FindLongestPalindrome("abcad")
	fmt.Println(result)
}
