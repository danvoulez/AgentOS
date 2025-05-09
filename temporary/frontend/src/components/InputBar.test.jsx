"use client"

// src/context/AuthContext.test.jsx
import { useContext } from "react"
import { render, screen, act, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { AuthProvider, default as AuthContext } from "./AuthContext" // Import Provider and Context
import apiClient from "../services/api" // Importar para mockar
import { BrowserRouter } from "react-router-dom" // Para o useNavigate dentro do AuthContext

// Mock apiClient (usar vi.mock para mockar o módulo inteiro)
vi.mock("../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    // Mockar interceptors se o AuthContext interagir com eles (geralmente não precisa)
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
  },
}))

// Mock do useNavigate (usado dentro do AuthContext)
const mockNavigate = vi.fn()
vi.mock("react-router-dom", async (importOriginal) => {
  const original = await importOriginal()
  return {
    ...original, // Manter outros exports
    useNavigate: () => mockNavigate, // Retornar nossa função mockada
  }
})

// --- Componente de Teste Consumidor ---
function TestAuthConsumer() {
  // Usar useContext diretamente para garantir que estamos testando o contexto exportado
  const context = useContext(AuthContext)

  if (!context) {
    return <div>Error: AuthContext is null</div>
  }

  const { token, user, isAuthenticated, loading, error, login, logout, fetchUser } = context

  return (
    <div>
      <div data-testid="auth-status">{isAuthenticated ? "Autenticado" : "Não Autenticado"}</div>
      <div data-testid="loading-status">{loading ? "Carregando" : "Parado"}</div>
      <div data-testid="user-info">{user ? `User: ${user.username} (${user.id})` : "Nenhum usuário"}</div>
      <div data-testid="token-info">{token || "Nenhum token"}</div>
      <div data-testid="error-info">{error || "Nenhum erro"}</div>
      <button onClick={() => login("test@user.com", "password123")}>Login</button>
      <button onClick={logout}>Logout</button>
      <button onClick={fetchUser}>Fetch User</button>
      {/* Botão para simular evento 401 */}
      <button onClick={() => window.dispatchEvent(new CustomEvent("auth-error-401"))}>Simulate 401</button>
    </div>
  )
}

// --- Suite de Testes ---
describe("AuthContext", () => {
  // Resetar mocks e localStorage antes de cada teste
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    // Garantir que apiClient mockado esteja limpo
    apiClient.get.mockReset()
    apiClient.post.mockReset()
    // Limpar chamadas do navigate mockado
    mockNavigate.mockClear()
  })

  // Limpar listeners de evento após cada teste
  afterEach(() => {
    // Precisa de uma forma de remover o listener adicionado pelo AuthProvider.
    // Isso é complexo de fazer externamente. Testar o efeito colateral (logout) é mais prático.
  })

  it("initial state: not authenticated, not loading, no user/token/error", () => {
    render(
      <BrowserRouter>
        {" "}
        {/* Necessário por causa do useNavigate */}
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      </BrowserRouter>,
    )
    expect(screen.getByTestId("auth-status")).toHaveTextContent("Não Autenticado")
    expect(screen.getByTestId("loading-status")).toHaveTextContent("Parado")
    expect(screen.getByTestId("user-info")).toHaveTextContent("Nenhum usuário")
    expect(screen.getByTestId("token-info")).toHaveTextContent("Nenhum token")
    expect(screen.getByTestId("error-info")).toHaveTextContent("Nenhum erro")
  })

  it("login successful: updates state, stores token, fetches user, navigates", async () => {
    const user = userEvent.setup()
    // Mockar respostas da API
    const mockToken = "fake-jwt-token-123"
    const mockUser = {
      id: "user-1",
      username: "test@user.com",
      email: "test@user.com",
      profile: { first_name: "Test" },
      roles: ["customer"],
      is_active: true,
    }
    apiClient.post.mockResolvedValueOnce({ data: { access_token: mockToken, token_type: "bearer" } })
    apiClient.get.mockResolvedValueOnce({ data: mockUser })

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      </BrowserRouter>,
    )

    const loginButton = screen.getByRole("button", { name: /login/i })

    // Usar 'act' para envolver ações que causam atualização de estado
    await act(async () => {
      await user.click(loginButton)
    })

    // Verificar estado de loading durante chamadas
    expect(screen.getByTestId("loading-status")).toHaveTextContent("Carregando")

    // Esperar que o loading termine (após login E fetchUser)
    await waitFor(() => expect(screen.getByTestId("loading-status")).toHaveTextContent("Parado"))

    // Verificar chamadas API
    expect(apiClient.post).toHaveBeenCalledWith("/auth/login", expect.any(URLSearchParams), expect.any(Object))
    expect(apiClient.get).toHaveBeenCalledWith("/users/me") // fetchUser chamado após login

    // Verificar estado final
    expect(screen.getByTestId("auth-status")).toHaveTextContent("Autenticado")
    expect(screen.getByTestId("user-info")).toHaveTextContent(`User: ${mockUser.username} (${mockUser.id})`)
    expect(screen.getByTestId("token-info")).toHaveTextContent(mockToken)
    expect(localStorage.getItem("authToken")).toBe(mockToken)
    expect(screen.getByTestId("error-info")).toHaveTextContent("Nenhum erro")

    // Verificar navegação
    expect(mockNavigate).toHaveBeenCalledWith("/comms") // Navegação padrão após login
  })

  it("login failure (API error): sets error state, does not authenticate", async () => {
    const user = userEvent.setup()
    const errorMessage = "Incorrect email or password"
    // Mockar API para falhar o POST de login
    apiClient.post.mockRejectedValueOnce(new Error(errorMessage)) // Simular erro de rede ou erro genérico
    // Alternativa: simular erro HTTP específico
    // apiClient.post.mockRejectedValueOnce({ response: { data: { detail: errorMessage }, status: 401 } });

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      </BrowserRouter>,
    )

    const loginButton = screen.getByRole("button", { name: /login/i })

    await act(async () => {
      await user.click(loginButton)
    })

    // Esperar loading terminar
    await waitFor(() => expect(screen.getByTestId("loading-status")).toHaveTextContent("Parado"))

    // Verificar API chamada
    expect(apiClient.post).toHaveBeenCalledTimes(1)
    expect(apiClient.get).not.toHaveBeenCalled() // fetchUser não deve ser chamado

    // Verificar estado final
    expect(screen.getByTestId("auth-status")).toHaveTextContent("Não Autenticado")
    expect(screen.getByTestId("user-info")).toHaveTextContent("Nenhum usuário")
    expect(screen.getByTestId("token-info")).toHaveTextContent("Nenhum token")
    expect(localStorage.getItem("authToken")).toBeNull()
    expect(screen.getByTestId("error-info")).toHaveTextContent(errorMessage) // Verificar mensagem de erro
    expect(mockNavigate).not.toHaveBeenCalled() // Não deve navegar
  })

  it("logout: clears state, removes token, navigates to login", async () => {
    const user = userEvent.setup()
    // Configurar estado inicial como logado
    const initialToken = "token-to-be-cleared"
    const initialUser = {
      id: "user-logged-in",
      username: "logged@in.com",
      email: "logged@in.com",
      profile: {},
      roles: [],
      is_active: true,
    }
    localStorage.setItem("authToken", initialToken)
    // Mock do fetchUser inicial que ocorre no useEffect do AuthProvider
    apiClient.get.mockResolvedValue({ data: initialUser })

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      </BrowserRouter>,
    )

    // Esperar o carregamento inicial do usuário terminar
    await waitFor(() => expect(screen.getByTestId("auth-status")).toHaveTextContent("Autenticado"))
    expect(screen.getByTestId("token-info")).toHaveTextContent(initialToken)
    expect(screen.getByTestId("user-info")).toHaveTextContent(`User: ${initialUser.username} (${initialUser.id})`)

    // Clicar no botão de logout
    const logoutButton = screen.getByRole("button", { name: /logout/i })
    await act(async () => {
      await user.click(logoutButton)
    })

    // Esperar que o estado seja limpo (geralmente síncrono, mas waitFor garante)
    await waitFor(() => expect(screen.getByTestId("auth-status")).toHaveTextContent("Não Autenticado"))

    // Verificar estado final
    expect(screen.getByTestId("user-info")).toHaveTextContent("Nenhum usuário")
    expect(screen.getByTestId("token-info")).toHaveTextContent("Nenhum token")
    expect(localStorage.getItem("authToken")).toBeNull()
    expect(screen.getByTestId("error-info")).toHaveTextContent("Nenhum erro") // Erro deve ser limpo

    // Verificar navegação para login
    expect(mockNavigate).toHaveBeenCalledWith("/login")
  })

  it("fetches user on initial load if valid token exists", async () => {
    const existingToken = "valid-existing-token"
    const existingUser = {
      id: "user-persisted",
      username: "persist@user.com",
      email: "persist@user.com",
      profile: { first_name: "Persisted" },
      roles: ["admin"],
      is_active: true,
    }
    localStorage.setItem("authToken", existingToken)
    // Mock da chamada /users/me que acontece no useEffect
    apiClient.get.mockResolvedValueOnce({ data: existingUser })

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      </BrowserRouter>,
    )

    // Esperar o fetchUser inicial terminar
    await waitFor(() => expect(screen.getByTestId("loading-status")).toHaveTextContent("Parado"))

    // Verificar se /users/me foi chamado
    expect(apiClient.get).toHaveBeenCalledWith("/users/me")

    // Verificar estado após fetch
    expect(screen.getByTestId("auth-status")).toHaveTextContent("Autenticado")
    expect(screen.getByTestId("user-info")).toHaveTextContent(`User: ${existingUser.username} (${existingUser.id})`)
    expect(screen.getByTestId("token-info")).toHaveTextContent(existingToken)
  })

  it("handles invalid token on initial load", async () => {
    const invalidToken = "invalid-or-expired-token"
    localStorage.setItem("authToken", invalidToken)
    // Mock para falhar a decodificação ou validação (isTokenValid retorna false)
    // jwtDecode será chamado internamente por isTokenValid, pode precisar mockar jwtDecode se o token for estruturalmente inválido
    vi.mock("jwt-decode", () => ({
      jwtDecode: vi.fn(() => {
        throw new Error("Invalid token")
      }),
    }))

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      </BrowserRouter>,
    )

    // Esperar um momento para o useEffect rodar
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10))
    })

    // Verificar que o estado permaneceu deslogado e o token foi removido
    expect(screen.getByTestId("auth-status")).toHaveTextContent("Não Autenticado")
    expect(screen.getByTestId("token-info")).toHaveTextContent("Nenhum token")
    expect(localStorage.getItem("authToken")).toBeNull()
    expect(apiClient.get).not.toHaveBeenCalledWith("/users/me") // Não deve tentar buscar user

    vi.restoreAllMocks() // Restaurar mock jwtDecode
  })

  it("handles 401 event by logging out", async () => {
    const user = userEvent.setup()
    // Configurar estado inicial como logado
    const initialToken = "token-that-will-be-invalidated"
    const initialUser = {
      id: "user-401",
      username: "error@user.com",
      email: "error@user.com",
      profile: {},
      roles: [],
      is_active: true,
    }
    localStorage.setItem("authToken", initialToken)
    apiClient.get.mockResolvedValue({ data: initialUser }) // Mock fetch inicial

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestAuthConsumer />
        </AuthProvider>
      </BrowserRouter>,
    )

    // Esperar autenticação inicial
    await waitFor(() => expect(screen.getByTestId("auth-status")).toHaveTextContent("Autenticado"))

    // Simular clique no botão que dispara o evento 401
    const simulateButton = screen.getByRole("button", { name: /simulate 401/i })
    await act(async () => {
      await user.click(simulateButton)
    })

    // Esperar que o logout seja processado e o estado atualizado
    await waitFor(() => expect(screen.getByTestId("auth-status")).toHaveTextContent("Não Autenticado"))

    // Verificar estado final (deslogado)
    expect(screen.getByTestId("user-info")).toHaveTextContent("Nenhum usuário")
    expect(screen.getByTestId("token-info")).toHaveTextContent("Nenhum token")
    expect(localStorage.getItem("authToken")).toBeNull()
    expect(mockNavigate).toHaveBeenCalledWith("/login") // Deve navegar para login após logout
  })
})
