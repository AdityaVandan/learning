package main

func ValidParenthesis(s string) bool {
	stack := []string{}
	openParenthesis := map[string]bool{"{": true, "[": true, "(": true}
	closeParenthesis := map[string]bool{"}": true, "]": true, ")": true}
	closeParenthesisReplacementMap := map[string]string{"}": "{", "]": "[", ")": "("}

	for _, c := range s {
		character := string(c)
		if _, exists := openParenthesis[character]; exists {
			stack = append(stack, character)
		} else if _, exists := closeParenthesis[character]; exists {
			if len(stack) == 0 {
				return false
			}
			replacementCharacter := closeParenthesisReplacementMap[character]
			if replacementCharacter == stack[len(stack)-1] {
				stack = stack[:len(stack)-1]
			} else {
				return false
			}
		}
	}
	if len(stack) == 0 {
		return true
	} else {
		return false
	}
}
