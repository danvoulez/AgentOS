import { render, screen, waitFor, act } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import RightHintsPanel from "./RightHintsPanel" // Componente real
import { useWebSocket } from "../hooks/useWebSocket" // Mockar Hook
import { useNavigate } from "react-router-dom" // Mockar Hook

// --- Mocks ---
vi.mock("../hooks/useWebSocket")
vi.mock("react-router-dom", async (importOriginal) => {
  const original = await importOriginal()
  return {
    ...original,
    useNavigate: vi.fn(), // Mock useNavigate
  }
})
// Mock date-fns (simplificado)
vi.mock("date-fns", () => ({
  formatDistanceToNow: vi.fn(() => "há pouco tempo"),
}))
vi.mock("date-fns/locale", () => ({ ptBR: {} })) // Mock locale object
vi.mock("uuid", () => ({ v4: vi.fn(() => `mock-uuid-${Math.random()}`) })) // Mock UUID generation

// --- Helper para Simular Mensagem WS ---
let mockLastJsonMessage = null // Variável de controle
const mockWebSocketHook = (lastMessage) => {
  useWebSocket.mockReturnValue({
    lastJsonMessage: lastMessage,
    isConnected: true,
    error: null,
    sendMessage: vi.fn(),
    connectWebSocket: vi.fn(),
    disconnectWebSocket: vi.fn(),
  })
}

// --- Mock do Navigate ---
const mockNavigateFn = vi.fn()

// --- Suite de Testes ---
describe("RightHintsPanel Component", () => {
  const user = userEvent.setup({ delay: null })

  beforeEach(() => {
    vi.clearAllMocks()
    mockLastJsonMessage = null
    mockWebSocketHook(null) // Resetar hook
    useNavigate.mockReturnValue(mockNavigateFn) // Resetar mock do navigate
    // Limpar DOM
    document.body.innerHTML = ""
  })

  const renderPanel = () => {
    return render(<RightHintsPanel />)
  }

  it("renders initial state with header and empty message", () => {
    renderPanel()
    expect(screen.getByRole("heading", { name: /fusion hints/i })).toBeInTheDocument()
    expect(screen.getByText("● Conectado")).toBeInTheDocument() // Status Conectado
    expect(screen.getByText(/sem hints no momento/i)).toBeInTheDocument()
  })

  it("displays a received hint with correct style and content", async () => {
    const hintPayload = {
      type: "suggestion", // Testar um tipo específico
      text: "Sugestão: Verificar pedido XYZ.",
      action: { label: "Ver Pedido", target: "/orders/xyz" },
    }
    mockLastJsonMessage = { type: "fusion_hint", payload: hintPayload }
    mockWebSocketHook(mockLastJsonMessage) // Aplicar o mock antes de renderizar

    const { rerender } = renderPanel() // Renderizar inicial
    rerender(<RightHintsPanel />) // Re-renderizar para pegar o novo lastJsonMessage

    // Esperar o hint aparecer
    await waitFor(() => {
      expect(screen.getByText("Sugestão: Verificar pedido XYZ.")).toBeInTheDocument()
      // Verificar se o botão de ação está lá
      expect(screen.getByRole("button", { name: /ver pedido/i })).toBeInTheDocument()
      // Verificar (indiretamente) o estilo pela presença do ícone correto
      const suggestionIcon = screen
        .getByText("Sugestão: Verificar pedido XYZ.")
        .closest("div.flex") // Container do card
        .querySelector("svg") // Achar o SVG do ícone
      // O teste de SVG pode ser frágil. Alternativa é verificar a classe do container.
      expect(suggestionIcon).toBeInTheDocument() // Verifica se há um SVG
      expect(suggestionIcon.querySelector('path[d^="M12"]')).toBeTruthy() // Exemplo: Checar path de LightBulbIcon (frágil)
      // Verificar classe de fundo/borda é mais robusto se as classes forem aplicadas corretamente
      expect(suggestionIcon.closest("div.border")).toHaveClass("bg-purple-800/50") // Checar classe do estilo
    })
  })

  it("displays multiple hints, prepending new ones, limiting to MAX_HINTS", async () => {
    const { rerender } = renderPanel()
    const MAX_HINTS = 10 // Conforme definido no componente

    // Simular recebimento de MAX_HINTS + 2 hints
    for (let i = 1; i <= MAX_HINTS + 2; i++) {
      const hint = { type: "info", text: `Hint ${i}` }
      mockLastJsonMessage = { type: "fusion_hint", payload: hint }
      mockWebSocketHook(mockLastJsonMessage)
      // Usar act para garantir que a atualização de estado seja processada
      await act(async () => {
        rerender(<RightHintsPanel />)
        await new Promise((res) => setTimeout(res, 0)) // Pequeno delay para garantir processamento
      })
    }

    // Esperar que o último hint esteja visível
    await waitFor(() => expect(screen.getByText(`Hint ${MAX_HINTS + 2}`)).toBeInTheDocument())

    // Verificar se apenas MAX_HINTS estão na tela
    // Usar queryAllByText para pegar todos os elementos com texto começando com "Hint"
    const hintElements = screen.queryAllByText(/^Hint d+$/)
    expect(hintElements).toHaveLength(MAX_HINTS)

    // Verificar se os hints mais recentes (MAX_HINTS+2 até 3) estão lá
    expect(screen.getByText(`Hint ${MAX_HINTS + 2}`)).toBeInTheDocument() // Último recebido
    expect(screen.getByText(`Hint ${MAX_HINTS + 1}`)).toBeInTheDocument()
    // ...
    expect(screen.getByText("Hint 3")).toBeInTheDocument() // O décimo mais recente

    // Verificar se os mais antigos (Hint 1, Hint 2) NÃO estão lá
    expect(screen.queryByText("Hint 1")).not.toBeInTheDocument()
    expect(screen.queryByText("Hint 2")).not.toBeInTheDocument()
  })

  it("dismisses a hint when the dismiss button is clicked", async () => {
    const hint1 = { type: "info", text: "Hint para deletar" }
    const hint2 = { type: "warning", text: "Hint para manter" }
    mockLastJsonMessage = { type: "fusion_hint", payload: hint1 }
    mockWebSocketHook(mockLastJsonMessage)
    const { rerender } = renderPanel()
    rerender(<RightHintsPanel />) // Render hint 1

    mockLastJsonMessage = { type: "fusion_hint", payload: hint2 }
    mockWebSocketHook(mockLastJsonMessage)
    rerender(<RightHintsPanel />) // Render hint 2

    await waitFor(() => {
      expect(screen.getByText("Hint para deletar")).toBeInTheDocument()
      expect(screen.getByText("Hint para manter")).toBeInTheDocument()
    })

    // Encontrar o botão de dismiss do primeiro hint
    const hintToDeleteElement = screen.getByText("Hint para deletar").closest('div[layout="position"]') // Encontrar o motion.div
    const dismissButton = within(hintToDeleteElement).getByTitle("Dispensar Hint")

    // Clicar no botão
    await user.click(dismissButton)

    // Verificar se o hint foi removido
    await waitFor(() => {
      expect(screen.queryByText("Hint para deletar")).not.toBeInTheDocument()
    })
    // Verificar se o outro hint permaneceu
    expect(screen.getByText("Hint para manter")).toBeInTheDocument()
  })

  it('calls navigate function when hint action with "target" is clicked', async () => {
    const hintPayload = {
      type: "info",
      text: "Navegar para orders",
      action: { label: "Ver Orders", target: "/orders" }, // Ação de navegação
    }
    mockLastJsonMessage = { type: "fusion_hint", payload: hintPayload }
    mockWebSocketHook(mockLastJsonMessage)
    const { rerender } = renderPanel()
    rerender(<RightHintsPanel />)

    const actionButton = await screen.findByRole("button", { name: /ver orders/i })
    await user.click(actionButton)

    // Verificar se navigate mock foi chamado com o target correto
    expect(mockNavigateFn).toHaveBeenCalledTimes(1)
    expect(mockNavigateFn).toHaveBeenCalledWith("/orders")
  })

  it('simulates structured command and navigates to /advisor when hint action with "intent" is clicked', async () => {
    // Mock window.alert (usado na simulação)
    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {})

    const hintPayload = {
      type: "alert",
      text: "Comando estruturado!",
      action: { label: "Executar Comando", intent: "approve_order", parameters: { order_id: 123 } }, // Ação estruturada
    }
    mockLastJsonMessage = { type: "fusion_hint", payload: hintPayload }
    mockWebSocketHook(mockLastJsonMessage)
    const { rerender } = renderPanel()
    rerender(<RightHintsPanel />)

    const actionButton = await screen.findByRole("button", { name: /executar comando/i })
    await user.click(actionButton)

    // Verificar se o alert (simulação) foi chamado com os dados corretos
    expect(alertSpy).toHaveBeenCalledTimes(1)
    expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("Intent: approve_order"))
    expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('"order_id": 123'))

    // Verificar se navigate foi chamado para ir ao advisor (comportamento da simulação)
    expect(mockNavigateFn).toHaveBeenCalledTimes(1)
    expect(mockNavigateFn).toHaveBeenCalledWith("/advisor")

    alertSpy.mockRestore() // Limpar spy
  })
})

// Helper
import { within } from "@testing-library/react"
