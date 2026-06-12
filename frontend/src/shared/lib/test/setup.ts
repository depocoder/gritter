import '@testing-library/jest-dom/vitest'

// Tokens and liked-state must not leak between test cases
beforeEach(() => {
  localStorage.clear()
})
