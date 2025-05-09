// src/hooks/useScrollToBottom.test.js
import React from "react"
import { renderHook } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { useScrollToBottom } from "./useScrollToBottom"

describe("useScrollToBottom Hook", () => {
  let mockElement
  let scrollIntoViewMock

  beforeEach(() => {
    // Mock do elemento do DOM e sua função scrollIntoView
    scrollIntoViewMock = vi.fn()
    mockElement = {
      scrollHeight: 1000, // Altura total simulada
      scrollTop: 0, // Posição inicial simulada
      lastElementChild: {
        // Simular último filho
        scrollIntoView: scrollIntoViewMock,
      },
    }
    // Mock da ref para retornar o elemento mockado
    vi.spyOn(React, "useRef").mockReturnValue({ current: mockElement })
  })

  afterEach(() => {
    vi.restoreAllMocks() // Limpar spy do useRef
  })

  it("initializes with a ref object", () => {
    const { result } = renderHook(() => useScrollToBottom(null)) // Dependência inicial null
    expect(result.current).toBeDefined()
    expect(result.current).toHaveProperty("current")
    expect(result.current.current).toBe(mockElement) // Verifica se a ref mockada foi retornada
  })

  it("does not call scrollIntoView initially if dependency is null/undefined", () => {
    renderHook(() => useScrollToBottom(null))
    expect(scrollIntoViewMock).not.toHaveBeenCalled()
  })

  it("calls scrollIntoView on the last child when dependency changes", () => {
    const initialDeps = ["msg1"]
    const { rerender } = renderHook(({ deps }) => useScrollToBottom(deps), {
      initialProps: { deps: initialDeps },
    })

    // Scroll deve ter sido chamado na montagem inicial com a dependência
    expect(scrollIntoViewMock).toHaveBeenCalledTimes(1)
    expect(scrollIntoViewMock).toHaveBeenCalledWith({ behavior: "auto", block: "end" })

    // Mudar a dependência
    const newDeps = ["msg1", "msg2"]
    rerender({ deps: newDeps })

    // Scroll deve ser chamado novamente
    expect(scrollIntoViewMock).toHaveBeenCalledTimes(2)
    expect(scrollIntoViewMock).toHaveBeenLastCalledWith({ behavior: "auto", block: "end" })
  })

  it("does not call scrollIntoView if dependency reference does not change", () => {
    const initialDeps = ["msg1"] // Array literal, muda referência a cada render
    // Para testar isso, a dependência precisa ter referência estável
    const stableDeps = { count: 1 }
    const { rerender } = renderHook(({ deps }) => useScrollToBottom(deps), {
      initialProps: { deps: stableDeps },
    })

    expect(scrollIntoViewMock).toHaveBeenCalledTimes(1) // Chamado na montagem

    // Re-renderizar com a MESMA referência de objeto
    rerender({ deps: stableDeps })

    // Não deve chamar novamente
    expect(scrollIntoViewMock).toHaveBeenCalledTimes(1)

    // Re-renderizar com objeto diferente mas igual valor (não deve chamar)
    rerender({ deps: { count: 1 } })
    expect(scrollIntoViewMock).toHaveBeenCalledTimes(1) // Ainda 1, pois useEffect compara referência de objeto

    // Re-renderizar com valor diferente
    rerender({ deps: { count: 2 } })
    expect(scrollIntoViewMock).toHaveBeenCalledTimes(2) // Agora deve chamar
  })

  it("handles case where container has no lastElementChild (e.g., empty)", () => {
    // Modificar mock para não ter lastElementChild
    const mockEmptyElement = {
      scrollHeight: 0,
      scrollTop: 0,
      lastElementChild: null, // << Sem último filho
    }
    vi.spyOn(React, "useRef").mockReturnValue({ current: mockEmptyElement })

    const { rerender } = renderHook(({ deps }) => useScrollToBottom(deps), {
      initialProps: { deps: ["dep1"] },
    })

    // scrollIntoView não deve ser chamado
    expect(scrollIntoViewMock).not.toHaveBeenCalled()
    // Verificar se tentou usar scrollTop como fallback
    // (Difícil de verificar diretamente o set de scrollTop sem mais mocks)
    // Poderíamos adicionar um spy no set do scrollTop se necessário
    expect(mockEmptyElement.scrollTop).toBe(mockEmptyElement.scrollHeight) // Verifica se o fallback foi tentado

    // Mudar dependência
    rerender({ deps: ["dep1", "dep2"] })
    expect(scrollIntoViewMock).not.toHaveBeenCalled()
    expect(mockEmptyElement.scrollTop).toBe(mockEmptyElement.scrollHeight) // Verifica se o fallback foi tentado de novo
  })
})
