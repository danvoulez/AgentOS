import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import ChatList from "./ChatList"
import apiClient from "../services/api" // Mock this
import { useWebSocket } from "../hooks/useWebSocket" // Mock this hook

// --- Mocks ---
vi.mock("../services/api")
vi.mock("../hooks/useWebSocket")

// Mock do componente filho para simplificar
vi.mock("./LoadingSpinner", () => ({ default: () => <div data-testid="loading-spinner">Loading...</div> }))

// Mock date-fns para ter data consistente nos testes
const mockDate = new Date(2024, 4, 15, 10, 30, 0) // 15 May 2024 10:30:00
vi.setSystemTime(mockDate) // Congelar tempo do sistema para os testes
vi.mock("date-fns", async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    formatDistanceToNow: vi.fn((date, options) => {
      // Simular retorno simples para testes
      if (!date) return "data inválida"
      const diff = (mockDate.getTime() - new Date(date).getTime()) / 1000 // Diff in seconds
      if (diff < 60) return "há menos de um minuto"
      if (diff < 3600) return `há ${Math.floor(diff / 60)} minutos`
      return `há ${Math.floor(diff / 3600)} horas` // Simplificado
    }),
  }
})
// Limpar mocks de data após testes
afterAll(() => {
  vi.useRealTimers()
})

// --- Dados Mockados ---
const mockChatsInitial = [
  {
    id: "waid1",
    contact_name: "Alice",
    last_message_preview: "Ok, entendido!",
    last_message_ts: new Date(2024, 4, 15, 10, 25, 0).toISOString(),
    unread_count: 0,
    mode: "human",
    status: "open",
  },
  {
    id: "waid2",
    contact_name: "Bob",
    last_message_preview: "Preciso de ajuda com...",
    last_message_ts: new Date(2024, 4, 15, 9, 15, 0).toISOString(),
    unread_count: 2,
    mode: "human",
    status: "open",
  },
  {
    id: "waid3",
    contact_name: "Charlie (Agent)",
    last_message_preview: "Verificando sistema...",
    last_message_ts: new Date(2024, 4, 14, 16, 0, 0).toISOString(),
    unread_count: 0,
    mode: "agent",
    status: "open",
  },
]

// --- Suite de Testes ---
describe("ChatList Component", () => {
  const user = userEvent.setup()
  let mockSetLastJsonMessage // Para simular WS
  let mockOnSelectChat

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks()
    apiClient.get.mockReset()
    mockSetLastJsonMessage = vi.fn() // Função dummy por padrão
    mockOnSelectChat = vi.fn()

    // Mock padrão do useWebSocket
    useWebSocket.mockReturnValue({
      lastJsonMessage: null,
      isConnected: true,
      error: null,
      sendMessage: vi.fn(),
      // Passar um setter mockado permite simular mensagens recebidas
      // Mas é mais simples chamar 'act' para atualizar 'lastJsonMessage' no teste
    })

    // Mock padrão da API GET /whatsapp/chats
    apiClient.get.mockResolvedValue({ data: [...mockChatsInitial] })
  })

  // Helper para renderizar
  const renderChatList = (selectedChatId = null) => {
    return render(<ChatList selectedChatId={selectedChatId} onSelectChat={mockOnSelectChat} />)
  }

  it("renders loading state initially", () => {
    // Impedir que a promise da API resolva imediatamente
    apiClient.get.mockImplementation(() => new Promise(() => {}))
    renderChatList()
    expect(screen.getByTestId("loading-spinner")).toBeInTheDocument()
  })

  it("fetches and displays chat list on mount", async () => {
    renderChatList()
    // Esperar o loading sumir e a API ser chamada
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith("/whatsapp/chats", expect.any(Object)))
    expect(screen.queryByTestId("loading-spinner")).not.toBeInTheDocument()

    // Verificar se os chats mockados foram renderizados
    expect(screen.getByText("Alice")).toBeInTheDocument()
    expect(screen.getByText("Ok, entendido!")).toBeInTheDocument()
    expect(screen.getByText("Bob")).toBeInTheDocument()
    expect(screen.getByText("Preciso de ajuda com...")).toBeInTheDocument()
    expect(screen.getByText("Charlie (Agent)")).toBeInTheDocument()
    // Verificar contagem não lida
    expect(screen.getByText("2")).toBeInTheDocument() // Badge de Bob
  })

  it("displays empty state message when no chats are found", async () => {
    apiClient.get.mockResolvedValue({ data: [] }) // Mock sem chats
    renderChatList()
    await waitFor(() => expect(apiClient.get).toHaveBeenCalled())
    expect(screen.getByText(/nenhuma conversa encontrada/i)).toBeInTheDocument()
  })

  it("displays error message on fetch failure", async () => {
    const errorMsg = "Falha na rede"
    apiClient.get.mockRejectedValue(new Error(errorMsg)) // Mock de falha
    renderChatList()
    await waitFor(() => expect(apiClient.get).toHaveBeenCalled())
    // O erro tratado pelo componente deve aparecer
    expect(await screen.findByText(/falha ao carregar conversas/i)).toBeInTheDocument()
  })

  it("calls onSelectChat with correct ID and resets unread count when an item is clicked", async () => {
    renderChatList()
    await waitFor(() => expect(screen.getByText("Bob")).toBeInTheDocument()) // Esperar renderizar

    const bobChatItem = screen.getByText("Bob").closest("li") // Encontrar o elemento <li>
    expect(bobChatItem).toBeInTheDocument()

    // Verificar badge inicial
    expect(within(bobChatItem).getByText("2")).toBeInTheDocument()

    // Clicar no chat de Bob
    await user.click(bobChatItem)

    // Verificar se onSelectChat foi chamado com o ID correto
    expect(mockOnSelectChat).toHaveBeenCalledTimes(1)
    expect(mockOnSelectChat).toHaveBeenCalledWith("waid2")

    // Verificar se o badge de não lido sumiu (atualização otimista)
    await waitFor(() => {
      expect(within(bobChatItem).queryByText("2")).not.toBeInTheDocument()
    })
  })

  it("updates chat preview and moves chat to top on new_whatsapp_message via WebSocket", async () => {
    // Mock inicial
    renderChatList()
    await waitFor(() => expect(screen.getByText("Alice")).toBeInTheDocument())

    // Simular recebimento de mensagem WS para Alice
    const newMessagePayload = {
      id: "wami-new",
      chat_id: "waid1", // Alice
      sender_id: "waid1", // Alice enviou
      content: "Nova mensagem recebida agora!",
      timestamp: new Date(2024, 4, 15, 10, 35, 0).toISOString(), // Mais recente
      metadata: { contact_name: "Alice" },
      // ... outros campos do payload
    }
    // Simular atualização do estado do hook useWebSocket
    useWebSocket.mockReturnValue({
      lastJsonMessage: { type: "new_whatsapp_message", payload: newMessagePayload },
      isConnected: true,
      error: null,
      sendMessage: vi.fn(),
    })

    // Re-renderizar ou esperar que o useEffect interno atualize
    // Em testes, precisamos forçar a atualização ou esperar
    // Re-renderizar é mais explícito aqui
    const { rerender } = render(<ChatList selectedChatId={null} onSelectChat={mockOnSelectChat} />)
    rerender(<ChatList selectedChatId={null} onSelectChat={mockOnSelectChat} />) // Força re-render com novo lastJsonMessage

    await waitFor(() => {
      // Verificar se o preview de Alice foi atualizado
      const aliceItem = screen.getByText("Alice").closest("li")
      expect(within(aliceItem).getByText(/nova mensagem recebida/i)).toBeInTheDocument()
      // Verificar se Alice está no topo (primeiro item da lista UL)
      const listItems = screen.getAllByRole("listitem") // Pega todos os <li>
      expect(listItems[0]).toBe(aliceItem)
    })
  })

  // TODO: Adicionar teste para atualização de modo via WS
  // TODO: Adicionar teste para incremento de unread_count via WS
})

// Helper para query dentro de um elemento
import { within } from "@testing-library/react"
