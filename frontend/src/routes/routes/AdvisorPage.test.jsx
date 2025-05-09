import { render, screen, waitFor, act } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import RightHintsPanel from "./RightHintsPanel" // Componente real
import { useWebSocket } from "../hooks/useWebSocket" // Mockar Hook

// --- Mocks ---
vi.mock("../hooks/useWebSocket")
// Mock useNavigate (já mockamos antes, mas garantir aqui também)
const mockNavigateFn = vi.fn()
vi.mock("react-router-dom", async (importOriginal) => {
  const original = await importOriginal()
  return {
    ...original,
    useNavigate: () => mockNavigateFn, // Retorna nosso mock
  }
})
// Mock date-fns (simplificado)
vi.mock("date-fns", () => ({
  formatDistanceToNow: vi.fn(() => "há alguns segundos"),
}))
vi.mock("date-fns/locale", () => ({ ptBR: {} })) // Mock locale object
// Mock UUID para IDs previsíveis (ajuda em snapshots ou seletores)
let uuidCounter = 0
vi.mock("uuid", () => ({ v4: vi.fn(() => `mock-uuid-${++uuidCounter}`) }))

// Mock window.alert (usado na simulação de ação estruturada)
window.alert = vi.fn()

// --- Helper para Simular Mensagem WS ---
let mockLastJsonMessage = null
const mockWebSocketHook = (lastMessage, isConnected = true, error = null) => {
  useWebSocket.mockReturnValue({
    lastJsonMessage: lastMessage,
    isConnected: isConnected,
    error: error,
    sendMessage: vi.fn(),
    connectWebSocket: vi.fn(),
    disconnectWebSocket: vi.fn(),
  })
}

// --- Suite de Testes ---
describe("RightHintsPanel Component", () => {
  const user = userEvent.setup({ delay: null })

  beforeEach(() => {
    vi.clearAllMocks()
    uuidCounter = 0 // Resetar contador UUID
    mockLastJsonMessage = null
    mockWebSocketHook(null) // Resetar hook
    mockNavigateFn.mockClear() // Limpar mock do navigate
    window.alert.mockClear() // Limpar mock do alert
    document.body.innerHTML = "" // Limpar DOM
  })

  const renderPanel = () => {
    return render(<RightHintsPanel />)
  }

  it("renders initial state with header (connected) and empty message", () => {
    renderPanel()
    expect(screen.getByRole("heading", { name: /fusion hints/i })).toBeInTheDocument()
    expect(screen.getByText("● Conectado")).toBeInTheDocument() // Status Conectado
    expect(screen.getByText(/sem hints no momento/i)).toBeInTheDocument()
    expect(screen.queryByTestId("hint-card")).not.toBeInTheDocument() // Nenhum card de hint
  })

  it("renders disconnected status and error if WS has error", () => {
    const wsErrorMsg = "Connection failed"
    mockWebSocketHook(null, false, wsErrorMsg) // Simular desconectado com erro
    renderPanel()
    expect(screen.getByText(/○ Desconectado (Erro!)/i)).toBeInTheDocument()
    expect(screen.getByTitle(wsErrorMsg)).toBeInTheDocument() // Verificar tooltip do erro
  })

  it("displays a received hint with correct style and content", async () => {
    const hintPayload = {
      type: "suggestion", // Testar um tipo específico
      text: "Sugestão: O cliente parece interessado no produto Y.",
      action: { label: "Ver Produto Y", target: "/products/y" },
    }
    mockLastJsonMessage = { type: "fusion_hint", payload: hintPayload }
    mockWebSocketHook(mockLastJsonMessage)

    const { rerender } = renderPanel()
    // Forçar re-render para pegar novo valor do hook
    rerender(<RightHintsPanel />)

    await waitFor(() => {
      expect(screen.getByText(hintPayload.text)).toBeInTheDocument()
      expect(screen.getByRole("button", { name: /ver produto y/i })).toBeInTheDocument()
      // Verificar estilo (ex: pela classe de fundo)
      const hintCard = screen.getByText(hintPayload.text).closest("div.border")
      expect(hintCard).toHaveClass("bg-purple-800/50") // Classe para suggestion
      expect(within(hintCard).getByTitle("Dispensar Hint")).toBeInTheDocument() // Botão de dismiss
    })
  })

  it("displays multiple hints, prepending new ones, respecting MAX_HINTS", async () => {
    const { rerender } = renderPanel()
    const MAX_HINTS = 10 // Conforme definido no componente

    // Simular recebimento de MAX_HINTS + 2 hints
    for (let i = 1; i <= MAX_HINTS + 2; i++) {
      const hint = { type: "info", text: `Hint ${i}` }
      mockLastJsonMessage = { type: "fusion_hint", payload: hint }
      mockWebSocketHook(mockLastJsonMessage)
      // Usar act para garantir processamento síncrono da atualização de estado
      await act(async () => {
        rerender(<RightHintsPanel />)
        // Esperar um tick para processamento assíncrono leve (se houver)
        await new Promise((res) => setTimeout(res, 0))
      })
    }

    // Esperar que o último hint (mais recente) esteja visível
    await waitFor(() => expect(screen.getByText(`Hint ${MAX_HINTS + 2}`)).toBeInTheDocument())

    // Verificar se apenas MAX_HINTS estão na tela
    const hintElements = screen.queryAllByText(/^Hint d+$/)
    expect(hintElements).toHaveLength(MAX_HINTS)

    // Verificar ordem (mais recente no topo)
    const firstHintText = hintElements[0].textContent
    const lastHintText = hintElements[MAX_HINTS - 1].textContent
    expect(firstHintText).toBe(`Hint ${MAX_HINTS + 2}`)
    expect(lastHintText).toBe(`Hint 3`) // (MAX_HINTS + 2) - MAX_HINTS + 1 = 3

    // Verificar se os mais antigos (Hint 1, Hint 2) NÃO estão lá
    expect(screen.queryByText("Hint 1")).not.toBeInTheDocument()
    expect(screen.queryByText("Hint 2")).not.toBeInTheDocument()
  })

  it("dismisses a hint when the dismiss button (X) is clicked", async () => {
    const hint1 = { type: "info", text: "Hint para deletar" }
    const hint2 = { type: "warning", text: "Hint para manter" }
    // Renderizar hint 1
    mockLastJsonMessage = { type: "fusion_hint", payload: hint1 }
    mockWebSocketHook(mockLastJsonMessage)
    const { rerender } = renderPanel()
    rerender(<RightHintsPanel />)
    // Renderizar hint 2 (será o primeiro da lista)
    mockLastJsonMessage = { type: "fusion_hint", payload: hint2 }
    mockWebSocketHook(mockLastJsonMessage)
    rerender(<RightHintsPanel />)

    await waitFor(() => {
      expect(screen.getByText("Hint para deletar")).toBeInTheDocument()
      expect(screen.getByText("Hint para manter")).toBeInTheDocument()
    })

    // Encontrar o botão de dismiss do hint1
    const hintToDeleteElement = screen.getByText("Hint para deletar").closest("div[layout]") // motion.div
    const dismissButton = within(hintToDeleteElement).getByTitle("Dispensar Hint")

    await user.click(dismissButton)

    // Verificar se foi removido (animação pode levar tempo, usar waitFor)
    await waitFor(() => {
      expect(screen.queryByText("Hint para deletar")).not.toBeInTheDocument()
    })
    // Verificar se o outro permaneceu
    expect(screen.getByText("Hint para manter")).toBeInTheDocument()
  })

  it('calls navigate function when hint action with "target" is clicked', async () => {
    const hintPayload = {
      type: "info",
      text: "Navegar para o dashboard",
      action: { label: "Ir para Dashboard", target: "/dashboard" },
    }
    mockLastJsonMessage = { type: "fusion_hint", payload: hintPayload }
    mockWebSocketHook(mockLastJsonMessage)
    const { rerender } = renderPanel()
    rerender(<RightHintsPanel />)

    const actionButton = await screen.findByRole("button", { name: /ir para dashboard/i })
    await user.click(actionButton)

    expect(mockNavigateFn).toHaveBeenCalledTimes(1)
    expect(mockNavigateFn).toHaveBeenCalledWith("/dashboard")
  })

  it('simulates structured command and navigates when hint action with "intent" is clicked', async () => {
    const hintPayload = {
      type: "alert",
      text: "Aprovar Pedido Urgente!",
      action: { label: "Aprovar Agora", intent: "approve_urgent_order", parameters: { orderRef: "ORD-URG-001" } },
    }
    mockLastJsonMessage = { type: "fusion_hint", payload: hintPayload }
    mockWebSocketHook(mockLastJsonMessage)
    const { rerender } = renderPanel()
    rerender(<RightHintsPanel />)

    const actionButton = await screen.findByRole("button", { name: /aprovar agora/i })
    await user.click(actionButton)

    // Verificar se o alert (simulação atual) foi chamado
    expect(window.alert).toHaveBeenCalledTimes(1)
    expect(window.alert).toHaveBeenCalledWith(expect.stringContaining("Intent: approve_urgent_order"))
    expect(window.alert).toHaveBeenCalledWith(expect.stringContaining('"orderRef": "ORD-URG-001"'))

    // Verificar se navigate foi chamado para /advisor (comportamento da simulação)
    expect(mockNavigateFn).toHaveBeenCalledTimes(1)
    expect(mockNavigateFn).toHaveBeenCalledWith("/advisor")

    // !! Observação: Quando a chamada real ao Gateway for implementada aqui (via context/hook),
    // este teste precisará ser atualizado para mockar essa chamada e verificar se ela ocorreu
    // em vez de verificar o window.alert.
  })

  it("ignores invalid hint payloads from WebSocket", async () => {
    const { rerender } = renderPanel()
    expect(screen.queryByTestId("hint-card")).not.toBeInTheDocument() // Nenhum card inicial

    // Enviar payload inválido (sem 'text')
    const invalidPayload = { type: "info", action: null }
    mockLastJsonMessage = { type: "fusion_hint", payload: invalidPayload }
    mockWebSocketHook(mockLastJsonMessage)
    rerender(<RightHintsPanel />)

    // Esperar um pouco para garantir que nada renderizou
    await act(async () => {
      await new Promise((res) => setTimeout(res, 50))
    })
    expect(screen.queryByTestId("hint-card")).not.toBeInTheDocument() // Ainda nenhum card

    // Enviar payload válido depois
    const validPayload = { type: "success", text: "Hint Válido" }
    mockLastJsonMessage = { type: "fusion_hint", payload: validPayload }
    mockWebSocketHook(mockLastJsonMessage)
    rerender(<RightHintsPanel />)

    // Agora deve aparecer
    expect(await screen.findByText("Hint Válido")).toBeInTheDocument()
  })
})

// Helper
import { within } from "@testing-library/react"
