"use client"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import AdvisorMessage from "./AdvisorMessage" // Componente real
import { AnimatePresence } from "framer-motion" // Necessário para motion

// --- Mocks ---
// Mock do hook useTypingEffect
const mockUseTypingEffect = vi.fn()
vi.mock("../hooks/useTypingEffect", () => ({
  useTypingEffect: mockUseTypingEffect,
}))

// Mock do SyntaxHighlighter
vi.mock("react-syntax-highlighter", () => ({
  Prism: ({ children, language, style }) => (
    <pre data-testid="syntax-highlighter" data-language={language} style={style}>
      <code>{children}</code>
    </pre>
  ),
}))
vi.mock("react-syntax-highlighter/dist/esm/styles/prism", () => ({
  atomDark: { backgroundColor: "mockAtomDark" }, // Mock do estilo
}))

// Mock do StructuredDataRenderer
vi.mock("./StructuredDataRenderer", () => ({
  // eslint-disable-next-line react/prop-types
  default: ({ data }) => <div data-testid="structured-renderer">{JSON.stringify(data)}</div>,
}))

// --- Dados Mockados ---
const userMessage = {
  id: "user1",
  role: "user",
  content: "Olá Advisor!",
  timestamp: new Date().toISOString(),
}
const aiTextMessage = {
  id: "ai1",
  role: "assistant",
  content: "Olá! Como posso ajudar?",
  timestamp: new Date().toISOString(),
  follow_up_actions: [],
  emotion: "neutral",
}
const aiMarkdownMessage = {
  id: "ai2",
  role: "assistant",
  content: '# Títulon* Item 1n* Item 2nn```jsnconsole.log("hello");n```',
  timestamp: new Date().toISOString(),
  follow_up_actions: [],
  emotion: "neutral",
}
const aiStructuredMessage = {
  // Simular dados estruturados como conteúdo
  id: "ai3",
  role: "assistant",
  content: { result: "data", value: 123, nested: { key: "val" } },
  timestamp: new Date().toISOString(),
  follow_up_actions: [],
  emotion: "informative",
}
const aiWithFollowUps = {
  id: "ai4",
  role: "assistant",
  content: "Deseja continuar?",
  timestamp: new Date().toISOString(),
  follow_up_actions: [
    { label: "Sim", action: { intent: "continue", parameters: {} } },
    { label: "Não", action: { intent: "stop", parameters: {} } },
  ],
  emotion: "questioning",
}
const aiErrorMessage = {
  // Simular uma mensagem de erro vinda do gateway
  id: "aiError1",
  role: "assistant",
  content: "⚠️ **Erro:** Falha ao buscar dados.",
  timestamp: new Date().toISOString(),
  follow_up_actions: [],
  emotion: "error",
}

// --- Suite de Testes ---
describe("AdvisorMessage Component", () => {
  const user = userEvent.setup({ delay: null })
  const mockFollowUpClick = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    // Mock padrão do useTypingEffect (digitação completa instantaneamente)
    mockUseTypingEffect.mockImplementation((text, speed) => ({
      displayedText: text,
      isComplete: true,
    }))
  })

  // Helper para renderizar dentro de AnimatePresence
  const renderWithMessage = (message) => {
    // Limpar DOM
    document.body.innerHTML = ""
    return render(
      <AnimatePresence>
        <AdvisorMessage message={message} onFollowUpClick={mockFollowUpClick} />
      </AnimatePresence>,
    )
  }

  it("renders user message correctly", () => {
    renderWithMessage(userMessage)
    const msgElement = screen.getByText(userMessage.content)
    expect(msgElement).toBeInTheDocument()
    // Verificar estilo/alinhamento (pai tem justify-end)
    const container = msgElement.closest("div.flex")
    expect(container).toHaveClass("justify-end")
    expect(msgElement.closest("div.rounded-lg")).toHaveClass("bg-fusion-blue") // Cor usuário
  })

  it("renders AI text message correctly after typing effect completes (mocked)", async () => {
    renderWithMessage(aiTextMessage)
    // Como mockamos isComplete=true, deve renderizar direto
    const msgElement = await screen.findByText(aiTextMessage.content) // Usar findBy para garantir que renderizou
    expect(msgElement).toBeInTheDocument()
    // Verificar estilo/alinhamento
    const container = msgElement.closest("div.flex")
    expect(container).toHaveClass("justify-start")
    expect(msgElement.closest("div.rounded-lg")).toHaveClass("bg-fusion-dark") // Cor AI
  })

  it("renders AI markdown message with formatting", async () => {
    renderWithMessage(aiMarkdownMessage)
    // Esperar a renderização do conteúdo Markdown
    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1, name: "Título" })).toBeInTheDocument()
      expect(screen.getByText("Item 1")).toBeInTheDocument()
      expect(screen.getByText("Item 2")).toBeInTheDocument()
      // Verificar o bloco de código renderizado pelo SyntaxHighlighter mockado
      const codeBlock = screen.getByTestId("syntax-highlighter")
      expect(codeBlock).toBeInTheDocument()
      expect(codeBlock).toHaveTextContent('console.log("hello");')
      expect(codeBlock).toHaveAttribute("data-language", "js")
    })
  })

  it("renders AI structured data using mocked StructuredDataRenderer", async () => {
    renderWithMessage(aiStructuredMessage)
    await waitFor(() => {
      const renderer = screen.getByTestId("structured-renderer")
      expect(renderer).toBeInTheDocument()
      // Verificar se o conteúdo passado foi o objeto original
      expect(renderer).toHaveTextContent(JSON.stringify(aiStructuredMessage.content))
    })
    // Verificar que ReactMarkdown NÃO foi chamado para este tipo
    // (Difícil de verificar diretamente sem mocks mais complexos, mas testamos o resultado)
  })

  it("renders AI error message content", async () => {
    renderWithMessage(aiErrorMessage)
    // O conteúdo é tratado como Markdown
    await waitFor(() => {
      expect(screen.getByText("Erro:", { exact: false })).toBeInTheDocument() // Parte do texto
      expect(screen.getByText("Falha ao buscar dados.", { exact: false })).toBeInTheDocument()
      // Verificar se está dentro de um elemento com role 'strong' devido ao Markdown
      expect(screen.getByText("Erro:").closest("strong")).toBeInTheDocument()
    })
  })

  it("renders follow-up buttons only when AI message is complete or structured", async () => {
    // 1. Teste com mensagem de texto INCOMPLETA
    mockUseTypingEffect.mockReturnValue({ displayedText: "Deseja...", isComplete: false })
    const { rerender } = renderWithMessage(aiWithFollowUps)
    expect(screen.queryByRole("button", { name: "Sim" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Não" })).not.toBeInTheDocument()

    // 2. Simular COMPLETO
    mockUseTypingEffect.mockReturnValue({ displayedText: aiWithFollowUps.content, isComplete: true })
    rerender(
      <AnimatePresence>
        <AdvisorMessage message={aiWithFollowUps} onFollowUpClick={mockFollowUpClick} />
      </AnimatePresence>,
    )
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Sim" })).toBeInTheDocument()
      expect(screen.getByRole("button", { name: "Não" })).toBeInTheDocument()
    })

    // 3. Teste com mensagem ESTRUTURADA (deve mostrar botões direto)
    const structuredWithFollowup = { ...aiStructuredMessage, follow_up_actions: aiWithFollowUps.follow_up_actions }
    renderWithMessage(structuredWithFollowup)
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Sim" })).toBeInTheDocument()
      expect(screen.getByRole("button", { name: "Não" })).toBeInTheDocument()
    })
  })

  it("calls onFollowUpClick handler with correct action payload when button is clicked", async () => {
    mockUseTypingEffect.mockReturnValue({ displayedText: aiWithFollowUps.content, isComplete: true })
    renderWithMessage(aiWithFollowUps)

    const buttonSim = await screen.findByRole("button", { name: "Sim" })
    const buttonNao = await screen.findByRole("button", { name: "Não" })

    // Clicar no 'Sim'
    await user.click(buttonSim)
    expect(mockFollowUpClick).toHaveBeenCalledTimes(1)
    expect(mockFollowUpClick).toHaveBeenCalledWith(aiWithFollowUps.follow_up_actions[0]) // Verifica payload da ação

    // Clicar no 'Não'
    await user.click(buttonNao)
    expect(mockFollowUpClick).toHaveBeenCalledTimes(2)
    expect(mockFollowUpClick).toHaveBeenCalledWith(aiWithFollowUps.follow_up_actions[1])
  })
})
