package main

import (
	"fmt"
	"os"
)

func main() {
	// take input from command line

	input := os.Args[1]
	fmt.Println("Input:", os.Args)
	result := ValidParenthesis(input)
	fmt.Println("Result:", result)
}
