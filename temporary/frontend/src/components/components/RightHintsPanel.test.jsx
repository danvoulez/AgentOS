"use client"

// src/routes/AdvisorPage.test.jsx
import React from "react"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { BrowserRouter } from "react-router-dom" // Para links/navigate na Sidebar
import AdvisorPage from "./AdvisorPage" // A página
import apiClient from "../services/api" // Mock API
import { useAuth } from "../hooks/useAuth" // Mock Hook

// --- Mocks ---
vi.mock("../services/api")
vi.mock("../hooks/useAuth")
vi.mock("../hooks/useScrollToBottom", () => ({ useScrollToBottom: vi.fn(() => React.createRef()) }))
vi.mock("../components/LoadingSpinner", () => ({ default: () => <div data-testid="loading-spinner">Loading...</div> }))
// Mockar componentes filhos complexos para focar na AdvisorPage
// Mock AdvisorHistorySidebar para controlar seu estado e métodos
const mockRefreshHistory = vi.fn()
vi.mock("../components/AdvisorHistorySidebar", () => ({
  // Usar forwardRef para que a ref funcione no componente mockado
  default: React.forwardRef(({ currentConversationId, onSelectConversation, onNewConversation, isLoading }, ref) => {
    // Expor a função mockada via ref
    React.useImperativeHandle(ref, () => ({
      refreshHistory: mockRefreshHistory,
    }))
    return (
      <div data-testid="advisor-history-sidebar">
        <button onClick={onNewConversation} disabled={isLoading}>
          Nova Conversa
        </button>
        <ul data-testid="advisor-history-list">
          {/* Renderizar itens dummy ou controlar via props/estado mockado */}
          <li onClick={() => onSelectConversation("conv1")} data-selected={currentConversationId === "conv1"}>
            Histórico 1 (ID: conv1)
            <button data-testid="delete-conv1">Del</button> {/* Botão delete dummy */}
          </li>
          <li onClick={() => onSelectConversation("conv2")} data-selected={currentConversationId === "conv2"}>
            Histórico 2 (ID: conv2)
            <button data-testid="delete-conv2">Del</button>
          </li>
        </ul>
        <button onClick={mockRefreshHistory}>Refresh Dummy</button>
      </div>
    )
  }),
}))
// Mock AdvisorMessage para verificar props passadas
vi.mock("../components/AdvisorMessage", () => ({
  default: ({ message, onFollowUpClick }) => (
    <div
      data-testid={`message-${message.role}-${message.id?.substring(0, 5)}`}
      data-content={typeof message.content === "string" ? message.content : JSON.stringify(message.content)}
    >
      Mensagem {message.role}
      {message.follow_up_actions?.map((action, i) => (
        <button key={i} onClick={() => onFollowUpClick(action)}>
          {action.label}
        </button>
      ))}
    </div>
  ),
}))

// --- Dados Mockados ---
const mockUser = {
  id: "user-test-advisor",
  email: "advisor@test.com",
  profile: { first_name: "AdvisorTest" },
  roles: ["admin"],
}
const mockConversationsList = [
  // Usado pelo Sidebar mockado implicitamente
  { id: "conv1", title: "Histórico 1", updated_at: new Date().toISOString() },
  { id: "conv2", title: "Histórico 2", updated_at: new Date(Date.now() - 100000).toISOString() },
]
const mockConversationDetailConv1 = {
  // Resposta para GET /conversations/conv1
  id: "conv1",
  user_id: "user-test-advisor",
  title: "Histórico 1",
  messages: [
    { role: "user", content: "Pergunta antiga 1", id: "u1", timestamp: new Date(Date.now() - 200000).toISOString() },
    {
      role: "assistant",
      content: "Resposta antiga 1",
      id: "a1",
      timestamp: new Date(Date.now() - 190000).toISOString(),
    },
  ],
}
const mockGatewayResponseNL = {
  // Resposta para POST /gateway/process (linguagem natural)
  conversation_id: "conv1", // Atualizando existente
  response_type: "natural_language_text",
  payload: { text: "Esta é a resposta da IA." },
  follow_up_actions: [{ label: "Saber mais", action: { intent: "details", parameters: {} } }],
  suggested_emotion: "informative",
  explanation: ["LLM call made", "Tool not needed"],
}
const mockGatewayResponseNewConv = {
  // Resposta para POST /gateway/process (nova conversa)
  conversation_id: "conv-new-123", // NOVO ID
  title: "Nova Conversa sobre Teste", // Título pode vir do backend
  response_type: "natural_language_text",
  payload: { text: "Começando uma nova conversa!" },
  follow_up_actions: [],
}
const mockGatewayResponseStructured = {
  // Resposta para POST /gateway/process (estruturada)
  conversation_id: "conv1",
  response_type: "structured_data",
  payload: { data: { result_count: 5, items: [1, 2, 3, 4, 5] } },
  follow_up_actions: [],
}

// --- Suite de Testes ---
describe("AdvisorPage Integration", () => {
  const user = userEvent.setup({ delay: null })

  beforeEach(() => {
    vi.clearAllMocks()
    // Mock useAuth
    useAuth.mockReturnValue({ user: mockUser, isAuthenticated: true })
    // Mock API Client
    apiClient.get.mockImplementation(async (url) => {
      await new Promise((res) => setTimeout(res, 10))
      if (url.includes("/advisor/conversations/conv1")) return { data: mockConversationDetailConv1 }
      // Simular erro ao buscar conv2 para testar erro
      if (url.includes("/advisor/conversations/conv2")) throw new Error("Falha simulada ao buscar conv2")
      // Chamada da lista (não usada diretamente pela página, mas pelo sidebar mockado)
      if (url.includes("/advisor/conversations")) return { data: mockConversationsList }
      return { data: null } // Default
    })
    apiClient.post.mockResolvedValue({ data: mockGatewayResponseNL }) // Default para NL
    apiClient.delete.mockResolvedValue({ status: 204, data: null })
    // Resetar mock de refresh do sidebar
    mockRefreshHistory.mockClear()
  })

  // Helper de Renderização
  const renderAdvisorPage = () => {
    document.body.innerHTML = ""
    render(
      <BrowserRouter>
        {" "}
        {/* Necessário para useNavigate no Sidebar (mesmo mockado) */}
        <AdvisorPage />
      </BrowserRouter>,
    )
  }

  it("renders sidebar, initial message, and input bar", () => {
    renderAdvisorPage()
    expect(screen.getByTestId("advisor-history-sidebar")).toBeInTheDocument()
    // Mensagem inicial (antes de selecionar conversa)
    expect(screen.getByText(/inicie uma nova conversa ou selecione/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/pergunte ao advisor/i)).toBeInTheDocument()
  })

  it("loads and displays messages when a conversation is selected from sidebar", async () => {
    renderAdvisorPage()
    // Simular clique no "Histórico 1" no sidebar mockado
    const historyItem1 = screen.getByText(/histórico 1/i)
    await user.click(historyItem1)

    // Verificar se API de detalhes foi chamada
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith("/advisor/conversations/conv1"))

    // Verificar se mensagens carregadas foram renderizadas (via mock do AdvisorMessage)
    expect(await screen.findByTestId("message-user-u1")).toBeInTheDocument()
    expect(screen.getByTestId("message-user-u1")).toHaveAttribute("data-content", "Pergunta antiga 1")
    expect(await screen.findByTestId("message-assistant-a1")).toBeInTheDocument()
    expect(screen.getByTestId("message-assistant-a1")).toHaveAttribute("data-content", "Resposta antiga 1")

    // Verificar se título principal atualizou
    expect(screen.getByRole("heading", { name: "Histórico 1" })).toBeInTheDocument()
  })

  it("displays error message if loading conversation messages fails", async () => {
    renderAdvisorPage()
    // Simular clique no "Histórico 2" (que mockamos para falhar)
    const historyItem2 = screen.getByText(/histórico 2/i)
    await user.click(historyItem2)

    // Verificar chamada API
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith("/advisor/conversations/conv2"))

    // Verificar mensagem de erro
    expect(await screen.findByText(/falha ao carregar histórico da conversa/i)).toBeInTheDocument()
    // Verificar se mensagens antigas (se houvesse) foram limpas
    expect(screen.queryByTestId(/message-/)).not.toBeInTheDocument()
    // Verificar se título resetou
    expect(screen.getByRole("heading", { name: "Advisor IA" })).toBeInTheDocument()
  })

  it("sends user message via InputBar, displays it, calls gateway, and displays NL response", async () => {
    renderAdvisorPage()
    // Selecionar Histórico 1 para ter um conversation_id
    await user.click(screen.getByText(/histórico 1/i))
    await waitFor(() => expect(screen.getByTestId("message-user-u1")).toBeInTheDocument()) // Esperar carregar

    const input = screen.getByPlaceholderText(/pergunte ao advisor/i)
    const sendButton = screen.getByRole("button", { name: /enviar/i }) // Assumindo que InputBar tem 'Enviar'

    // Digitar e enviar
    await user.type(input, "Nova pergunta para IA")
    await user.click(sendButton)

    // Verificar se mensagem do usuário apareceu (mockada)
    expect(await screen.findByTestId(/message-user-user-/)).toBeInTheDocument() // ID gerado com timestamp
    expect(screen.getByTestId(/message-user-user-/)).toHaveAttribute("data-content", "Nova pergunta para IA")

    // Verificar se API POST foi chamada com dados corretos
    await waitFor(() => expect(apiClient.post).toHaveBeenCalledTimes(1))
    expect(apiClient.post).toHaveBeenCalledWith(
      "/gateway/process",
      expect.objectContaining({
        conversation_id: "conv1",
        user_id: mockUser.id,
        request_type: "natural_language",
        payload: { text: "Nova pergunta para IA" },
      }),
      expect.any(Object),
    ) // O terceiro arg pode ser config Axios

    // Verificar se resposta NL da IA apareceu (mockada)
    expect(await screen.findByTestId(/message-assistant-assis-/)).toBeInTheDocument()
    expect(screen.getByTestId(/message-assistant-assis-/)).toHaveAttribute(
      "data-content",
      mockGatewayResponseNL.payload.text,
    )

    // Verificar se botão de follow-up apareceu
    expect(screen.getByRole("button", { name: /saber mais/i })).toBeInTheDocument()
  })

  it("sends message without conversation_id, receives new ID, and calls refreshHistory", async () => {
    apiClient.post.mockResolvedValue({ data: mockGatewayResponseNewConv }) // Configurar resposta com novo ID

    renderAdvisorPage() // Iniciar sem conversa selecionada
    const input = screen.getByPlaceholderText(/pergunte ao advisor/i)
    const sendButton = screen.getByRole("button", { name: /enviar/i })

    await user.type(input, "Pergunta para nova conversa")
    await user.click(sendButton)

    // Verificar POST sem conversation_id
    await waitFor(() =>
      expect(apiClient.post).toHaveBeenCalledWith(
        "/gateway/process",
        expect.objectContaining({
          conversation_id: null, // << Importante
          payload: { text: "Pergunta para nova conversa" },
        }),
        expect.any(Object),
      ),
    )

    // Verificar se resposta apareceu
    expect(await screen.findByTestId(/message-assistant-assis-/)).toHaveTextContent(/começando uma nova conversa/i)

    // Verificar se o título da página atualizou
    expect(screen.getByRole("heading", { name: mockGatewayResponseNewConv.title })).toBeInTheDocument()

    // Verificar se refreshHistory do Sidebar mockado foi chamado
    await waitFor(() => expect(mockRefreshHistory).toHaveBeenCalled())
  })

  it("handles and displays structured data response", async () => {
    apiClient.post.mockResolvedValue({ data: mockGatewayResponseStructured }) // Configurar resposta estruturada

    renderAdvisorPage()
    await user.click(screen.getByText(/histórico 1/i)) // Selecionar conv
    await waitFor(() => expect(screen.getByTestId("message-user-u1")).toBeInTheDocument())

    const input = screen.getByPlaceholderText(/pergunte ao advisor/i)
    await user.type(input, "Me dê dados estruturados")
    await user.click(screen.getByRole("button", { name: /enviar/i }))

    await waitFor(() => expect(apiClient.post).toHaveBeenCalled())

    // Verificar se a mensagem da IA foi renderizada E passou os dados corretos para o mock do AdvisorMessage
    const assistantMessage = await screen.findByTestId(/message-assistant-assis-/)
    expect(assistantMessage).toBeInTheDocument()
    // O mock do AdvisorMessage exibe o data-content como JSON string
    expect(assistantMessage).toHaveAttribute("data-content", JSON.stringify(mockGatewayResponseStructured.payload.data))
  })

  it("calls sendMessageToGateway with follow-up context when follow-up button is clicked", async () => {
    apiClient.post.mockResolvedValue({ data: mockGatewayResponseNL }) // Configurar resposta inicial com follow-up

    renderAdvisorPage()
    await user.click(screen.getByText(/histórico 1/i))
    await waitFor(() => expect(screen.getByTestId("message-user-u1")).toBeInTheDocument())

    const input = screen.getByPlaceholderText(/pergunte ao advisor/i)
    await user.type(input, "Pergunta inicial")
    await user.click(screen.getByRole("button", { name: /enviar/i }))

    // Esperar resposta e botão de follow-up
    const followUpButton = await screen.findByRole("button", { name: /saber mais/i })

    // Limpar mock do POST para verificar a nova chamada
    apiClient.post.mockClear()
    apiClient.post.mockResolvedValue({
      data: { ...mockGatewayResponseNL, payload: { text: "Aqui estão mais detalhes." }, follow_up_actions: [] },
    }) // Resposta do follow-up

    // Clicar no botão de follow-up
    await user.click(followUpButton)

    // Verificar se a segunda chamada POST foi feita corretamente
    await waitFor(() => expect(apiClient.post).toHaveBeenCalledTimes(1))
    expect(apiClient.post).toHaveBeenCalledWith(
      "/gateway/process",
      expect.objectContaining({
        conversation_id: "conv1",
        payload: { text: "Saber mais" }, // O texto enviado é o label do botão
        // O contexto deve incluir a ação original do follow-up
        context: expect.objectContaining({
          follow_up_origin: mockGatewayResponseNL.follow_up_actions[0].action,
        }),
      }),
      expect.any(Object),
    )

    // Verificar se a resposta do follow-up apareceu
    expect(await screen.findByText("Aqui estão mais detalhes.")).toBeInTheDocument()
  })
})
