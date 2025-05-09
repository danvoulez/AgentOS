// src/components/MessageView.test.jsx
import React from "react"
import { render, screen, waitFor, act } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach, afterAll } from "vitest"
import MessageView from "./MessageView" // O componente a ser testado
import apiClient from "../services/api" // Mockar API
import { useWebSocket } from "../hooks/useWebSocket" // Mockar Hook
import { useAuth } from "../hooks/useAuth" // Mockar Hook

// --- Mocks ---
vi.mock("../services/api")
vi.mock("../hooks/useWebSocket")
vi.mock("../hooks/useAuth")
vi.mock("../hooks/useScrollToBottom", () => ({
  // Mockar o hook de scroll
  useScrollToBottom: vi.fn(() => React.createRef()), // Retorna uma ref mockada
}))
vi.mock("./LoadingSpinner", () => ({ default: () => <div data-testid="loading-spinner">Loading...</div> }))

// Mock date-fns
const mockDate = new Date(2024, 4, 15, 11, 0, 0)
vi.useFakeTimers()
vi.setSystemTime(mockDate)
vi.mock("date-fns", async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    format: vi.fn((date, formatStr, options) => {
      if (!date) return "inválido"
      try {
        const d = new Date(date)
        if (d.toDateString() === mockDate.toDateString()) {
          return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}` // HH:mm for today
        } else {
          return `${d.getDate().toString().padStart(2, "0")}/${(d.getMonth() + 1).toString().padStart(2, "0")} ${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}` // dd/MM HH:mm for others
        }
      } catch {
        return "inválido"
      }
    }),
  }
})
afterAll(() => {
  vi.useRealTimers()
})

// --- Dados Mockados ---
const mockMessagesChat1 = [
  {
    id: "wami1",
    chat_id: "chat1",
    sender_id: "chat1",
    content: "Olá!",
    type: "text",
    timestamp: new Date(2024, 4, 15, 10, 50, 0).toISOString(),
    status: "received",
    created_at: new Date(2024, 4, 15, 10, 50, 1).toISOString(),
  },
  {
    id: "msg-me-1",
    chat_id: "chat1",
    sender_id: "employee:me@test.com",
    content: "Oi, como posso ajudar?",
    type: "text",
    timestamp: new Date(2024, 4, 15, 10, 51, 0).toISOString(),
    status: "read",
    created_at: new Date(2024, 4, 15, 10, 51, 1).toISOString(),
  },
  {
    id: "wami2",
    chat_id: "chat1",
    sender_id: "chat1",
    content: "audio.ogg",
    type: "audio",
    timestamp: new Date(2024, 4, 15, 10, 52, 0).toISOString(),
    status: "received",
    transcription: "Transcrição do áudio aqui",
    created_at: new Date(2024, 4, 15, 10, 52, 1).toISOString(),
  },
  {
    id: "msg-me-2",
    chat_id: "chat1",
    sender_id: "employee:me@test.com",
    content: "Entendido.",
    type: "text",
    timestamp: new Date(2024, 4, 15, 10, 53, 0).toISOString(),
    status: "delivered",
    created_at: new Date(2024, 4, 15, 10, 53, 1).toISOString(),
  },
  {
    id: "wami3",
    chat_id: "chat1",
    sender_id: "chat1",
    content: "image.jpg",
    type: "image",
    timestamp: new Date(2024, 4, 15, 10, 54, 0).toISOString(),
    status: "received",
    created_at: new Date(2024, 4, 15, 10, 54, 1).toISOString(),
  },
]

// --- Suite de Testes ---
describe("MessageView Component", () => {
  let mockLastJsonMessage = null

  // Função helper para mockar o hook useWebSocket
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

  beforeEach(() => {
    vi.clearAllMocks()
    apiClient.get.mockReset()
    mockLastJsonMessage = null

    // Mock padrão useAuth
    useAuth.mockReturnValue({
      user: { id: "user-me", email: "me@test.com" }, // Identificador do usuário logado
      isAuthenticated: true,
    })
    // Mock padrão useWebSocket
    mockWebSocketHook(null)
    // Mock padrão API GET /messages
    apiClient.get.mockResolvedValue({ data: [...mockMessagesChat1] })
  })

  const renderMessageView = (chatId) => {
    document.body.innerHTML = "" // Limpar DOM
    return render(<MessageView chatId={chatId} />)
  }

  it("shows loading state initially when chatId is provided", () => {
    apiClient.get.mockImplementation(() => new Promise(() => {}))
    renderMessageView("chat1")
    expect(screen.getByTestId("loading-spinner")).toBeInTheDocument()
  })

  it('shows "select a chat" message when no chatId is provided', () => {
    renderMessageView(null)
    expect(screen.getByText(/selecione uma conversa/i)).toBeInTheDocument()
    expect(apiClient.get).not.toHaveBeenCalled()
  })

  it("fetches and displays messages for the selected chatId, differentiating own messages", async () => {
    renderMessageView("chat1")
    await waitFor(() =>
      expect(apiClient.get).toHaveBeenCalledWith("/whatsapp/chats/chat1/messages", expect.any(Object)),
    )
    expect(screen.queryByTestId("loading-spinner")).not.toBeInTheDocument()

    // Check content
    expect(screen.getByText("Olá!")).toBeInTheDocument()
    expect(screen.getByText("Oi, como posso ajudar?")).toBeInTheDocument()
    expect(screen.getByText("audio.ogg")).toBeInTheDocument()
    expect(screen.getByText("Entendido.")).toBeInTheDocument()
    expect(screen.getByText("image.jpg")).toBeInTheDocument()
    expect(screen.getByText(/transcrição do áudio aqui/i)).toBeInTheDocument()

    // Check styling (own vs other) - based on sender_id 'employee:me@test.com'
    const ownMessage1 = screen.getByText("Oi, como posso ajudar?").closest("div.rounded-lg")
    const ownMessage2 = screen.getByText("Entendido.").closest("div.rounded-lg")
    const receivedMessage1 = screen.getByText("Olá!").closest("div.rounded-lg")
    const receivedMessageAudio = screen.getByText("audio.ogg").closest("div.rounded-lg")
    const receivedMessageImage = screen.getByText("image.jpg").closest("div.rounded-lg")

    expect(ownMessage1).toHaveClass("bg-fusion-purple") // Classe para 'own'
    expect(ownMessage2).toHaveClass("bg-fusion-purple")
    expect(receivedMessage1).toHaveClass("bg-fusion-dark") // Classe para 'received'
    expect(receivedMessageAudio).toHaveClass("bg-fusion-dark")
    expect(receivedMessageImage).toHaveClass("bg-fusion-dark")

    // Check status icons for own messages
    expect(within(ownMessage1).getByTitle("Lido")).toBeInTheDocument() // status 'read'
    expect(within(ownMessage2).getByTitle("Entregue")).toBeInTheDocument() // status 'delivered'
  })

  it("displays empty state message when chat has no messages", async () => {
    apiClient.get.mockResolvedValue({ data: [] })
    renderMessageView("chat1")
    await waitFor(() => expect(apiClient.get).toHaveBeenCalled())
    expect(screen.getByText(/nenhuma mensagem nesta conversa/i)).toBeInTheDocument()
  })

  it("displays error message on fetch failure", async () => {
    const errorMsg = "Erro de servidor"
    apiClient.get.mockRejectedValue(new Error(errorMsg))
    renderMessageView("chat1")
    await waitFor(() => expect(apiClient.get).toHaveBeenCalled())
    expect(await screen.findByText(/falha ao carregar mensagens/i)).toBeInTheDocument()
  })

  it("appends new message received via WebSocket for the current chat", async () => {
    renderMessageView("chat1")
    await waitFor(() => expect(screen.getByText("Olá!")).toBeInTheDocument())

    // Simular nova mensagem WS
    const newMessagePayload = {
      id: "msg-ws-new",
      chat_id: "chat1",
      sender_id: "chat1", // Message from contact
      content: "Nova mensagem via WS!",
      type: "text",
      timestamp: new Date(2024, 4, 15, 11, 5, 0).toISOString(),
      status: "received",
      created_at: new Date().toISOString(),
    }
    mockWebSocketHook({ type: "new_whatsapp_message", payload: newMessagePayload })
    const { rerender } = render(<MessageView chatId="chat1" />)
    rerender(<MessageView chatId="chat1" />)

    // Verificar se a nova mensagem apareceu no final
    await waitFor(() => {
      expect(screen.getByText("Nova mensagem via WS!")).toBeInTheDocument()
    })
    // Check if it's styled as received message
    expect(screen.getByText("Nova mensagem via WS!").closest("div.rounded-lg")).toHaveClass("bg-fusion-dark")
  })

  it("updates message status via WebSocket for the current chat", async () => {
    renderMessageView("chat1")
    // Esperar mensagem 'msg-me-2' (nossa) aparecer com status 'delivered'
    await waitFor(() => expect(screen.getByText("Entendido.")).toBeInTheDocument())
    let msgElement = screen.getByText("Entendido.").closest("div.rounded-lg")
    expect(within(msgElement).getByTitle("Entregue")).toBeInTheDocument()
    expect(within(msgElement).getByTitle("Entregue")).toHaveClass("text-fusion-blue")

    // Simular atualização de status para 'read'
    const statusUpdatePayload = {
      id: "msg-me-2",
      chat_id: "chat1",
      status: "read",
      timestamp: new Date(2024, 4, 15, 11, 6, 0).toISOString(),
    }
    mockWebSocketHook({ type: "whatsapp_message_status", payload: statusUpdatePayload })
    const { rerender } = render(<MessageView chatId="chat1" />)
    rerender(<MessageView chatId="chat1" />)

    // Verificar se o status da mensagem foi atualizado para 'read'
    await waitFor(() => {
      msgElement = screen.getByText("Entendido.").closest("div.rounded-lg")
      expect(within(msgElement).getByTitle("Lido")).toBeInTheDocument()
      expect(within(msgElement).getByTitle("Lido")).toHaveClass("text-fusion-teal") // Cor de 'read'
    })
  })

  it("ignores WebSocket messages for other chats", async () => {
    renderMessageView("chat1") // Visualizando chat1
    await waitFor(() => expect(screen.getByText("Olá!")).toBeInTheDocument())

    // Simular nova mensagem WS para chat2
    const otherChatMessagePayload = {
      id: "other-msg",
      chat_id: "chat2",
      sender_id: "chat2",
      content: "Ignore this",
      type: "text",
      timestamp: new Date().toISOString(),
      created_at: new Date().toISOString(),
    }
    mockWebSocketHook({ type: "new_whatsapp_message", payload: otherChatMessagePayload })
    const { rerender } = render(<MessageView chatId="chat1" />)
    rerender(<MessageView chatId="chat1" />)

    // Aguardar um pouco
    await act(async () => {
      await new Promise((res) => setTimeout(res, 50))
    })

    // Verificar que a mensagem NÃO apareceu
    expect(screen.queryByText("Ignore this")).not.toBeInTheDocument()
  })
})

// Helper
import { within } from "@testing-library/react"
