import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { MemoryRouter, Routes, Route } from "react-router-dom" // Usar MemoryRouter
import LoginPage from "./LoginPage"
import { AuthProvider } from "../context/AuthContext" // Importar Provider real

// --- Mock Parcial do AuthContext ---
// Vamos mockar apenas as funções e estados que LoginPage usa DIRETAMENTE
// O Provider real será usado, mas o hook retornará valores mockados.
const mockLogin = vi.fn()
const mockUseAuth = vi.fn()

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => mockUseAuth(), // Retornar o mock da função que retorna o objeto de contexto
}))

// --- Mock de uma Rota Protegida para Teste de Redirecionamento ---
function MockProtectedPage() {
  return <div data-testid="protected-page">Protected Page Content</div>
}

// --- Suite de Testes ---
describe("LoginPage Component", () => {
  const user = userEvent.setup()

  beforeEach(() => {
    // Resetar mocks antes de cada teste
    mockLogin.mockReset()
    mockUseAuth.mockReset()
    // Configurar mock padrão do useAuth para estado não logado
    mockUseAuth.mockReturnValue({
      login: mockLogin,
      loading: false,
      error: null,
      isAuthenticated: false,
      user: null,
      // Incluir outras funções/estados se LoginPage precisar deles
      logout: vi.fn(),
      fetchUser: vi.fn(),
    })
  })

  // Helper para renderizar LoginPage dentro dos providers necessários
  const renderLoginPage = (initialEntries = ["/login"]) => {
    // Usar MemoryRouter para controlar a rota inicial e simular navegação
    render(
      <MemoryRouter initialEntries={initialEntries}>
        <AuthProvider>
          {" "}
          {/* Usar Provider real para que useAuth funcione */}
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/comms" element={<MockProtectedPage />} /> {/* Rota dummy para redirecionamento */}
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    )
  }

  it("renders login form correctly", () => {
    renderLoginPage()
    expect(screen.getByRole("heading", { name: /fusion login/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/senha/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /entrar/i })).toBeInTheDocument()
  })

  it("allows typing in email and password fields", async () => {
    renderLoginPage()
    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/senha/i)

    await user.type(emailInput, "user@test.com")
    await user.type(passwordInput, "mypassword")

    expect(emailInput).toHaveValue("user@test.com")
    expect(passwordInput).toHaveValue("mypassword")
  })

  it("calls login function from useAuth on form submit", async () => {
    renderLoginPage()
    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/senha/i)
    const submitButton = screen.getByRole("button", { name: /entrar/i })

    await user.type(emailInput, "test@login.com")
    await user.type(passwordInput, "correctpassword")
    await user.click(submitButton)

    // Verificar se a função login do contexto mockado foi chamada
    expect(mockLogin).toHaveBeenCalledTimes(1)
    expect(mockLogin).toHaveBeenCalledWith("test@login.com", "correctpassword")
  })

  it("displays loading state when login is in progress", async () => {
    // Configurar mock para simular loading
    mockUseAuth.mockReturnValue({
      login: mockLogin,
      loading: true, // <<< Simular loading
      error: null,
      isAuthenticated: false,
      user: null,
      logout: vi.fn(),
      fetchUser: vi.fn(),
    })

    renderLoginPage()

    // Verificar se o botão mostra estado de loading
    expect(screen.getByRole("button", { name: /entrando/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /entrando/i })).toBeDisabled()
    expect(screen.getByLabelText(/email/i)).toBeDisabled()
    expect(screen.getByLabelText(/senha/i)).toBeDisabled()
  })

  it("displays error message if login fails", async () => {
    const errorMessage = "Credenciais inválidas!"
    // Configurar mock para simular erro
    mockUseAuth.mockReturnValue({
      login: mockLogin.mockRejectedValue(new Error(errorMessage)), // Mockar login para rejeitar
      loading: false,
      error: errorMessage, // <<< Simular erro no estado
      isAuthenticated: false,
      user: null,
      logout: vi.fn(),
      fetchUser: vi.fn(),
    })

    renderLoginPage()
    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/senha/i)
    const submitButton = screen.getByRole("button", { name: /entrar/i })

    await user.type(emailInput, "wrong@user.com")
    await user.type(passwordInput, "wrongpass")
    await user.click(submitButton)

    // Esperar a exibição do erro (pode ser assíncrono se o estado de erro atualizar após a promise rejeitar)
    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument()
    })
    // Garantir que o botão voltou ao estado normal (não loading)
    expect(screen.getByRole("button", { name: /entrar/i })).toBeEnabled()
  })

  it("redirects to target page if already authenticated", () => {
    // Configurar mock para simular autenticado
    mockUseAuth.mockReturnValue({
      login: mockLogin,
      loading: false,
      error: null,
      isAuthenticated: true, // <<< Simular autenticado
      user: { id: "test", username: "test" },
      logout: vi.fn(),
      fetchUser: vi.fn(),
    })

    // Renderizar na rota /login
    renderLoginPage(["/login"])

    // Verificar se o conteúdo da página protegida foi renderizado (indicando redirecionamento)
    // O useEffect dentro de LoginPage deve navegar para /comms
    expect(screen.queryByRole("heading", { name: /fusion login/i })).not.toBeInTheDocument()
    expect(screen.getByTestId("protected-page")).toBeInTheDocument() // Verifica se chegou na rota protegida
  })

  it('redirects to specified "from" location after login if available', async () => {
    // Mock login para resolver e simular a navegação feita pelo AuthContext
    mockLogin.mockImplementation(async () => {
      // Simular o AuthContext navegando para onde veio
      // O mock do useNavigate já está configurado
      mockNavigate("/dashboard", { replace: true })
      return Promise.resolve() // Indicar sucesso
    })

    render(
      <MemoryRouter initialEntries={[{ pathname: "/login", state: { from: { pathname: "/dashboard" } } }]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/dashboard" element={<div data-testid="dashboard-page">Dashboard</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    )

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/senha/i)
    const submitButton = screen.getByRole("button", { name: /entrar/i })

    await user.type(emailInput, "user@test.com")
    await user.type(passwordInput, "password")
    await user.click(submitButton)

    // Verificar se o login foi chamado
    expect(mockLogin).toHaveBeenCalledTimes(1)

    // Verificar se a navegação ocorreu para a página original ('/dashboard')
    // A navegação é feita pelo AuthContext (mockado aqui via mockLogin -> mockNavigate)
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/dashboard", { replace: true })
    })
  })
})
