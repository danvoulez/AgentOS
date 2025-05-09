// src/routes/CommsPage.test.jsx
import React from "react"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import CommsPage from "./CommsPage" // A página a ser testada
import apiClient from "../services/api" // Mock API
// Mockar contextos e hooks usados pela página e seus filhos
import { AuthProvider } from "../context/AuthContext"
import { WebSocketProvider } from "../context/WebSocketContext"
import { useAuth } from "../hooks/useAuth"
import { useWebSocket } from "../hooks/useWebSocket"
import { BrowserRouter } from "react-router-dom" // Para navegação interna se houver

// --- Mocks ---
vi.mock("../services/api")
vi.mock("../hooks/useAuth")
vi.mock("../hooks/useWebSocket")
// Não mockar os componentes filhos (ChatList, MessageView, InputBar) para testar a integração REAL
vi.mock("../hooks/useScrollToBottom", () => ({ useScrollToBottom: vi.fn(() => React.createRef()) })) // Mock scroll
vi.mock("../components/LoadingSpinner", () => ({ default: () => <div data-testid="loading-spinner">Loading...</div> }))

// --- Dados Mockados ---
const mockUser = { id: "user-me", email: "me@test.com", profile: { first_name: "Me" }, roles: ["employee"] }
const mockChats = [
  {
    id: "waid1",
    contact_name: "Alice",
    last_message_preview: "Msg A",
    last_message_ts: new Date(Date.now() - 200000).toISOString(),
    unread_count: 0,
    mode: "human",
    status: "open",
  },
  {
    id: "waid2",
    contact_name: "Bob",
    last_message_preview: "Msg B",
    last_message_ts: new Date(Date.now() - 100000).toISOString(),
    unread_count: 1,
    mode: "human",
    status: "open",
  },
]
const mockMessagesChat1 = [
  {
    id: "m1",
    chat_id: "waid1",
    sender_id: "waid1",
    content: "Mensagem de Alice",
    type: "text",
    timestamp: new Date(Date.now() - 190000).toISOString(),
    created_at: new Date().toISOString(),
  },
]
const mockMessagesChat2 = [
  {
    id: "m2",
    chat_id: "waid2",
    sender_id: "waid2",
    content: "Mensagem inicial de Bob",
    type: "text",
    timestamp: new Date(Date.now() - 90000).toISOString(),
    created_at: new Date().toISOString(),
  },
  {
    id: "m3-me",
    chat_id: "waid2",
    sender_id: "employee:me@test.com",
    content: "Resposta minha para Bob",
    type: "text",
    timestamp: new Date(Date.now() - 80000).toISOString(),
    created_at: new Date().toISOString(),
    status: "read",
  },
]

// --- Suite de Testes ---
describe("CommsPage Integration", () => {
  const user = userEvent.setup({ delay: null })

  beforeEach(() => {
    vi.clearAllMocks()
    // Mock useAuth
    useAuth.mockReturnValue({ user: mockUser, isAuthenticated: true })
    // Mock useWebSocket
    useWebSocket.mockReturnValue({
      lastJsonMessage: null,
      isConnected: true,
      error: null,
      sendMessage: vi.fn(),
      connectWebSocket: vi.fn(),
      disconnectWebSocket: vi.fn(),
    })
    // Mock API calls
    apiClient.get.mockImplementation(async (url, config) => {
      await new Promise((res) => setTimeout(res, 10)) // Simular pequeno delay
      if (url.includes("/whatsapp/chats") && !url.includes("/messages")) {
        return { data: mockChats }
      }
      if (url.includes("/whatsapp/chats/waid1/messages")) {
        return { data: mockMessagesChat1 }
      }
      if (url.includes("/whatsapp/chats/waid2/messages")) {
        return { data: mockMessagesChat2 }
      }
      return { data: [] } // Default empty
    })
    apiClient.post.mockResolvedValue({ data: { status: "queued", internal_message_id: "new-msg-id-test" } }) // Mock send success
  })

  // Helper de Renderização
  const renderCommsPage = () => {
    document.body.innerHTML = ""
    render(
      <BrowserRouter>
        <AuthProvider>
          <WebSocketProvider>
            <CommsPage />
          </WebSocketProvider>
        </AuthProvider>
      </BrowserRouter>,
    )
  }

  it("renders ChatList and initial placeholder message view", async () => {
    renderCommsPage()
    // Esperar ChatList carregar
    expect(await screen.findByText("Alice")).toBeInTheDocument()
    expect(await screen.findByText("Bob")).toBeInTheDocument()
    // Verificar placeholder inicial na área de mensagens
    expect(screen.getByText(/selecione uma conversa/i)).toBeInTheDocument()
    // Verificar que InputBar NÃO está visível ou está em modo placeholder
    expect(screen.queryByPlaceholderText(/digite sua mensagem/i)).not.toBeInTheDocument()
  })

  it("loads messages in MessageView and enables InputBar when a chat is selected from ChatList", async () => {
    renderCommsPage()
    const aliceChat = await screen.findByText("Alice") // Esperar Alice carregar
    const bobChat = await screen.findByText("Bob") // Esperar Bob carregar

    // Clicar em "Bob"
    await user.click(bobChat.closest("li"))

    // Verificar se API de mensagens foi chamada para Bob (waid2)
    await waitFor(() =>
      expect(apiClient.get).toHaveBeenCalledWith("/whatsapp/chats/waid2/messages", expect.any(Object)),
    )

    // Verificar se as mensagens de Bob apareceram
    expect(await screen.findByText("Mensagem inicial de Bob")).toBeInTheDocument()
    expect(await screen.findByText("Resposta minha para Bob")).toBeInTheDocument()
    // Verificar se placeholder sumiu
    expect(screen.queryByText(/selecione uma conversa/i)).not.toBeInTheDocument()
    // Verificar se InputBar apareceu e está habilitado
    expect(screen.getByPlaceholderText(/digite sua mensagem/i)).toBeInTheDocument()
    // Botão de envio deve estar inicialmente desabilitado (draft vazio)
    expect(screen.getByRole("button", { name: /enviar mensagem/i })).toBeDisabled()
  })

  it("allows typing and sends message via InputBar when a chat is selected", async () => {
    renderCommsPage()
    // Selecionar Bob
    const bobChat = await screen.findByText("Bob")
    await user.click(bobChat.closest("li"))
    // Esperar InputBar aparecer
    const input = await screen.findByPlaceholderText(/digite sua mensagem/i)
    const sendButton = screen.getByRole("button", { name: /enviar mensagem/i })

    // Digitar na InputBar
    await user.type(input, "Testando envio!")
    expect(input).toHaveValue("Testando envio!")
    // Botão deve habilitar após digitar
    expect(sendButton).toBeEnabled()

    // Clicar no botão de enviar
    await user.click(sendButton)

    // Verificar se a API POST foi chamada corretamente
    expect(apiClient.post).toHaveBeenCalledTimes(1)
    expect(apiClient.post).toHaveBeenCalledWith("/whatsapp/send", {
      recipient_wa_id: "waid2", // ID do chat selecionado (Bob)
      content: "Testando envio!",
    })

    // Verificar se o input foi limpo após sucesso simulado
    await waitFor(() => {
      expect(input).toHaveValue("")
    })
    // Botão deve desabilitar novamente
    expect(sendButton).toBeDisabled()
  })

  it("displays error below InputBar if sending message fails", async () => {
    const sendErrorMsg = "Falha no Servidor de Envio"
    apiClient.post.mockRejectedValueOnce(new Error(sendErrorMsg)) // Mock de falha no envio

    renderCommsPage()
    // Selecionar Bob
    const bobChat = await screen.findByText("Bob")
    await user.click(bobChat.closest("li"))
    const input = await screen.findByPlaceholderText(/digite sua mensagem/i)
    const sendButton = screen.getByRole("button", { name: /enviar mensagem/i })

    // Digitar e Enviar
    await user.type(input, "Mensagem que falhará")
    await user.click(sendButton)

    // Verificar se a API foi chamada
    expect(apiClient.post).toHaveBeenCalledTimes(1)

    // Verificar se a mensagem de erro apareceu (procurar texto próximo ao input)
    expect(await screen.findByText(`Erro ao enviar: ${sendErrorMsg}`)).toBeInTheDocument()

    // Verificar se o input NÃO foi limpo
    expect(input).toHaveValue("Mensagem que falhará")
    // Botão deve estar habilitado ainda (pois há texto)
    expect(sendButton).toBeEnabled()
  })
})
