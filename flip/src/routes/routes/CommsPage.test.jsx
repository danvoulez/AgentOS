// src/hooks/useTypingEffect.test.js
import { renderHook, act } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { useTypingEffect } from "./useTypingEffect" // Importar o hook real

describe("useTypingEffect Hook", () => {
  beforeEach(() => {
    vi.useFakeTimers() // Usar timers falsos para controlar setInterval/setTimeout
  })

  afterEach(() => {
    vi.useRealTimers() // Restaurar timers reais
    vi.clearAllTimers() // Limpar quaisquer timers pendentes
  })

  it("initializes with empty string and isComplete as false", () => {
    const { result } = renderHook(() => useTypingEffect("Hello", 10))
    expect(result.current.displayedText).toBe("")
    expect(result.current.isComplete).toBe(false)
  })

  it("displays text character by character based on speed", () => {
    const text = "Hi"
    const speed = 50
    const { result } = renderHook(() => useTypingEffect(text, speed))

    // Initial state
    expect(result.current.displayedText).toBe("")
    expect(result.current.isComplete).toBe(false)

    // Advance time just enough for the first character timeout
    act(() => {
      vi.advanceTimersByTime(speed)
    })
    expect(result.current.displayedText).toBe("H")
    expect(result.current.isComplete).toBe(false)

    // Advance time for the second character interval
    act(() => {
      vi.advanceTimersByTime(speed)
    })
    expect(result.current.displayedText).toBe("Hi")
    // Should be complete now
    expect(result.current.isComplete).toBe(true)

    // Advance time further, should not change anything
    act(() => {
      vi.advanceTimersByTime(speed * 5)
    })
    expect(result.current.displayedText).toBe("Hi")
    expect(result.current.isComplete).toBe(true)
  })

  it("sets isComplete to true immediately when typing finishes", () => {
    const text = "Done"
    const speed = 10
    const { result } = renderHook(() => useTypingEffect(text, speed))

    // Advance exactly the time needed
    act(() => {
      vi.advanceTimersByTime(speed * text.length)
    }) // Time for first char + intervals for rest

    expect(result.current.displayedText).toBe(text)
    expect(result.current.isComplete).toBe(true)
  })

  it("handles empty string input correctly", () => {
    const { result } = renderHook(() => useTypingEffect("", 10))
    expect(result.current.displayedText).toBe("")
    expect(result.current.isComplete).toBe(true) // Should be complete immediately
    // Advance time, should not change
    act(() => {
      vi.advanceTimersByTime(100)
    })
    expect(result.current.displayedText).toBe("")
    expect(result.current.isComplete).toBe(true)
  })

  it("handles zero or negative typing speed correctly", () => {
    const text = "Fast"
    const { result } = renderHook(() => useTypingEffect(text, 0))
    // Should display full text immediately and be complete
    expect(result.current.displayedText).toBe(text)
    expect(result.current.isComplete).toBe(true)

    const { result: resultNeg } = renderHook(() => useTypingEffect(text, -10))
    expect(resultNeg.current.displayedText).toBe(text)
    expect(resultNeg.current.isComplete).toBe(true)
  })

  it("clears interval on unmount", () => {
    const clearIntervalSpy = vi.spyOn(global, "clearInterval")
    const clearTimeoutSpy = vi.spyOn(global, "clearTimeout")
    const { unmount } = renderHook(() => useTypingEffect("Testing cleanup", 10))

    // Interval/Timeout should be active initially
    expect(clearIntervalSpy).not.toHaveBeenCalled()
    expect(clearTimeoutSpy).not.toHaveBeenCalled()

    unmount()

    // Check if cleanup functions were called
    expect(clearIntervalSpy).toHaveBeenCalledTimes(1)
    expect(clearTimeoutSpy).toHaveBeenCalledTimes(1) // Includes first char timeout

    clearIntervalSpy.mockRestore() // Clean up spy
    clearTimeoutSpy.mockRestore()
  })

  it("resets and restarts typing when fullText changes", () => {
    const text1 = "First"
    const text2 = "Second"
    const speed = 10
    const { result, rerender } = renderHook(({ text }) => useTypingEffect(text, speed), {
      initialProps: { text: text1 },
    })

    // Type part of the first text
    act(() => {
      vi.advanceTimersByTime(speed * 3)
    }) // Fi + r
    expect(result.current.displayedText).toBe("Fir")
    expect(result.current.isComplete).toBe(false)

    // Change the text prop
    rerender({ text: text2 })

    // State should reset immediately
    expect(result.current.displayedText).toBe("")
    expect(result.current.isComplete).toBe(false)

    // Advance time to type the new text
    act(() => {
      vi.advanceTimersByTime(speed * text2.length)
    }) // Time for S + econd
    expect(result.current.displayedText).toBe(text2)
    expect(result.current.isComplete).toBe(true)
  })

  it("resets correctly when text changes to empty string", () => {
    const text1 = "Some text"
    const speed = 10
    const { result, rerender } = renderHook(({ text }) => useTypingEffect(text, speed), {
      initialProps: { text: text1 },
    })

    // Type part of the first text
    act(() => {
      vi.advanceTimersByTime(speed * 4)
    })
    expect(result.current.displayedText).toBe("Some")
    expect(result.current.isComplete).toBe(false)

    // Change text to empty
    rerender({ text: "" })

    // Should reset and be complete
    expect(result.current.displayedText).toBe("")
    expect(result.current.isComplete).toBe(true)
    // Advance time, nothing should happen
    act(() => {
      vi.advanceTimersByTime(100)
    })
    expect(result.current.displayedText).toBe("")
    expect(result.current.isComplete).toBe(true)
  })
})
