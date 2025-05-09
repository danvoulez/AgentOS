"use client"

// src/components/AdvisorHistorySidebar.test.jsx
import React, { forwardRef } from "react"
import { render, screen, waitFor, act } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach, afterAll } from "vitest"
import AdvisorHistorySidebar from "./AdvisorHistorySidebar" // Componente real
import apiClient from "../services/api" // Mock API
import { BrowserRouter } from "react-router-dom" // Necessário se usar NavLink/Link internamente

// --- Mocks ---
vi.mock("../services/api")
// Mock useAuth (embora o token possa ser gerenciado pelo interceptor)
vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({ token: "mock-token-unused", user: { id: "test-user" } }), // Fornecer um token dummy se necessário
}))
vi.mock("./LoadingSpinner", () => ({ default: () => <div data-testid="loading-spinner">Loading...</div> }))

// Mock date-fns
const mockDate = new Date(2024, 4, 15, 12, 0, 0)
vi.useFakeTimers()
vi.setSystemTime(mockDate)
vi.mock("date-fns", async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    formatDistanceToNow: vi.fn((date, options) => {
      if (!date) return "data inválida"
      try {
        const diff = (mockDate.getTime() - new Date(date).getTime()) / 1000
        if (diff < 5) return "agora mesmo"
        if (diff < 60) return "há menos de um minuto"
        return `há ${Math.floor(diff / 60)} min`
      } catch {
        return "data inválida"
      }
    }),
  }
})
afterAll(() => {
  vi.useRealTimers()
})

// Mock window.confirm
window.confirm = vi.fn(() => true) // Default to true (confirm delete)

// --- Dados Mockados ---
const mockConversations = [
  { id: "conv1", title: "Conversa sobre Vendas", updated_at: new Date(2024, 4, 15, 11, 55, 0).toISOString() },
  { id: "conv2", title: "Dúvidas de Entrega", updated_at: new Date(2024, 4, 15, 11, 30, 0).toISOString() },
  { id: "conv3", title: "Consulta Produto X", updated_at: new Date(2024, 4, 14, 18, 0, 0).toISOString() },
]

// --- Suite de Testes ---
describe("AdvisorHistorySidebar Component", () => {
  const user = userEvent.setup({ delay: null })
  let mockOnSelectConversation
  let mockOnNewConversation
  let sidebarRef // Para testar o método refreshHistory

  // Componente Wrapper para capturar a ref
  const SidebarWithRef = forwardRef((props, ref) => (
    <BrowserRouter>
      <AdvisorHistorySidebar ref={ref} {...props} />
    </BrowserRouter>
  ))
  SidebarWithRef.displayName = "SidebarWithRef" // Adicionar nome para debug

  beforeEach(() => {
    vi.clearAllMocks()
    window.confirm.mockClear().mockReturnValue(true) // Resetar e default para true
    mockOnSelectConversation = vi.fn()
    mockOnNewConversation = vi.fn()
    sidebarRef = React.createRef() // Criar nova ref para cada teste

    // Mock padrão da API GET (sucesso)
    apiClient.get.mockResolvedValue({ data: [...mockConversations] })
    // Mock padrão da API DELETE (sucesso)
    apiClient.delete.mockResolvedValue({ status: 204, data: null })
  })

  // Helper de Renderização
  const renderSidebar = (props = {}) => {
    const defaultProps = {
      currentConversationId: null,
      onSelectConversation: mockOnSelectConversation,
      onNewConversation: mockOnNewConversation,
      isLoading: false,
    }
    return render(<SidebarWithRef ref={sidebarRef} {...defaultProps} {...props} />)
  }

  it("renders loading state initially", () => {
    apiClient.get.mockImplementation(() => new Promise(() => {})) // Manter pendente
    renderSidebar()
    expect(screen.getByTestId("loading-spinner")).toBeInTheDocument()
    // Botão Nova Conversa deve estar desabilitado durante loading
    expect(screen.getByRole("button", { name: /nova conversa/i })).toBeDisabled()
  })

  it("fetches and displays conversation list sorted by date", async () => {
    renderSidebar()
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith("/advisor/conversations", expect.any(Object)))
    expect(screen.queryByTestId("loading-spinner")).not.toBeInTheDocument()

    // Verificar se os itens aparecem NA ORDEM CORRETA (mais recente primeiro)
    const listItems = screen.getAllByRole("listitem") // Assumindo que ConversationItem renderiza <li> implicitamente via motion.div
    expect(listItems).toHaveLength(3)
    expect(within(listItems[0]).getByText("Conversa sobre Vendas")).toBeInTheDocument() // Mais recente
    expect(within(listItems[1]).getByText("Dúvidas de Entrega")).toBeInTheDocument()
    expect(within(listItems[2]).getByText("Consulta Produto X")).toBeInTheDocument() // Mais antigo
  })

  it("displays empty message when no conversations exist", async () => {
    apiClient.get.mockResolvedValue({ data: [] })
    renderSidebar()
    await waitFor(() => expect(apiClient.get).toHaveBeenCalled())
    expect(screen.getByText(/nenhuma conversa ainda/i)).toBeInTheDocument()
  })

  it("displays error message on fetch failure", async () => {
    apiClient.get.mockRejectedValue(new Error("Network Error"))
    renderSidebar()
    await waitFor(() => expect(apiClient.get).toHaveBeenCalled())
    expect(await screen.findByText(/falha ao carregar histórico/i)).toBeInTheDocument()
  })

  it('calls onNewConversation when "Nova Conversa" button is clicked', async () => {
    renderSidebar()
    await waitFor(() => expect(apiClient.get).toHaveBeenCalled()) // Esperar carregar
    const newConvButton = screen.getByRole("button", { name: /nova conversa/i })
    await user.click(newConvButton)
    expect(mockOnNewConversation).toHaveBeenCalledTimes(1)
  })

  it("calls onSelectConversation with correct ID when a conversation item is clicked", async () => {
    renderSidebar()
    await waitFor(() => expect(screen.getByText("Dúvidas de Entrega")).toBeInTheDocument())
    const deliveryConvItem = screen.getByText("Dúvidas de Entrega").closest('div[role="listitem"]') // Buscar pelo div com motion
    await user.click(deliveryConvItem)
    expect(mockOnSelectConversation).toHaveBeenCalledTimes(1)
    expect(mockOnSelectConversation).toHaveBeenCalledWith("conv2") // ID da conversa clicada
  })

  it("highlights the selected conversation item", async () => {
    renderSidebar({ currentConversationId: "conv2" }) // Passar ID selecionado
    await waitFor(() => expect(screen.getByText("Dúvidas de Entrega")).toBeInTheDocument())
    const deliveryConvItem = screen.getByText("Dúvidas de Entrega").closest('div[role="listitem"]')
    const salesConvItem = screen.getByText("Conversa sobre Vendas").closest('div[role="listitem"]')
    // Verificar classes de highlight (ajustar se as classes mudarem)
    expect(deliveryConvItem).toHaveClass("bg-fusion-purple/60")
    expect(salesConvItem).not.toHaveClass("bg-fusion-purple/60")
  })

  it("calls delete API and removes item when delete icon is clicked and confirmed", async () => {
    window.confirm.mockReturnValue(true) // Simular confirmação
    renderSidebar({ currentConversationId: "conv1" }) // Simular uma conversa selecionada
    await waitFor(() => expect(screen.getByText("Dúvidas de Entrega")).toBeInTheDocument())

    const deliveryConvItem = screen.getByText("Dúvidas de Entrega").closest('div[role="listitem"]')
    const deleteButton = within(deliveryConvItem).getByTitle("Deletar conversa")

    // Mostrar botão ao passar o mouse (simulado com fireEvent ou focando)
    // userEvent.hover(deliveryConvItem); // userEvent.hover pode ser instável
    // await waitFor(() => expect(deleteButton).toBeVisible()); // Visibilidade pode ser difícil

    // Clicar diretamente no botão delete
    await user.click(deleteButton)

    // Verificar confirmação
    expect(window.confirm).toHaveBeenCalledTimes(1)
    expect(window.confirm).toHaveBeenCalledWith('Tem certeza que deseja deletar a conversa "Dúvidas de Entrega"?')

    // Verificar chamada DELETE API
    await waitFor(() => expect(apiClient.delete).toHaveBeenCalledWith("/advisor/conversations/conv2"))

    // Verificar remoção otimista do item da UI
    expect(screen.queryByText("Dúvidas de Entrega")).not.toBeInTheDocument()
    expect(screen.getByText("Conversa sobre Vendas")).toBeInTheDocument() // Outras permanecem
    expect(screen.getByText("Consulta Produto X")).toBeInTheDocument()

    // Verificar se onNewConversation NÃO foi chamado (porque a deletada não era a selecionada)
    expect(mockOnNewConversation).not.toHaveBeenCalled()
  })

  it("calls onNewConversation if the *currently selected* conversation is deleted", async () => {
    window.confirm.mockReturnValue(true)
    renderSidebar({ currentConversationId: "conv2" }) // CONV2 está selecionada
    await waitFor(() => expect(screen.getByText("Dúvidas de Entrega")).toBeInTheDocument())

    const deliveryConvItem = screen.getByText("Dúvidas de Entrega").closest('div[role="listitem"]')
    const deleteButton = within(deliveryConvItem).getByTitle("Deletar conversa")
    await user.click(deleteButton)

    expect(window.confirm).toHaveBeenCalledTimes(1)
    await waitFor(() => expect(apiClient.delete).toHaveBeenCalledWith("/advisor/conversations/conv2"))
    expect(screen.queryByText("Dúvidas de Entrega")).not.toBeInTheDocument()

    // Verificar se onNewConversation FOI chamado
    expect(mockOnNewConversation).toHaveBeenCalledTimes(1)
  })

  it("does NOT call delete API if confirmation is cancelled", async () => {
    window.confirm.mockReturnValue(false) // Simular cancelamento
    renderSidebar()
    await waitFor(() => expect(screen.getByText("Dúvidas de Entrega")).toBeInTheDocument())
    const deliveryConvItem = screen.getByText("Dúvidas de Entrega").closest('div[role="listitem"]')
    const deleteButton = within(deliveryConvItem).getByTitle("Deletar conversa")
    await user.click(deleteButton)

    expect(window.confirm).toHaveBeenCalledTimes(1)
    expect(apiClient.delete).not.toHaveBeenCalled() // API não deve ser chamada
    expect(screen.getByText("Dúvidas de Entrega")).toBeInTheDocument() // Item não deve ser removido
  })

  it("calls fetchHistory when refresh button is clicked", async () => {
    renderSidebar()
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledTimes(1)) // Chamada inicial

    const refreshButton = screen.getByRole("button", { name: /atualizar histórico/i })
    await user.click(refreshButton)

    // Verificar se API foi chamada novamente
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledTimes(2))
  })

  it("calls refreshHistory method via ref", async () => {
    renderSidebar()
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledTimes(1))

    // Chamar método exposto pela ref
    act(() => {
      sidebarRef.current?.refreshHistory()
    })

    // Verificar se API foi chamada novamente
    await waitFor(() => expect(apiClient.get).toHaveBeenCalledTimes(2))
  })
})

// Helper
import { within } from "@testing-library/react"
