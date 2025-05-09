"use client"

// src/context/AuthContext.jsx
import { createContext, useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { jwtDecode } from "jwt-decode" // Use named import
import axios from "axios"

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 segundos
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("authToken")
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  },
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // Handle 401 authentication errors
    if (error.response && error.response.status === 401) {
      localStorage.removeItem("authToken")
      if (window.location.pathname !== "/login") {
        window.location.href = "/login"
      }
    }
    return Promise.reject(error)
  },
)

// Criar o Contexto
const AuthContext = createContext(null)

// Helper para verificar token
const isTokenValid = (token) => {
  if (!token) return false
  try {
    const decoded = jwtDecode(token)
    const currentTime = Date.now() / 1000
    return decoded.exp > currentTime
  } catch (error) {
    console.error("Erro ao decodificar token no AuthContext:", error)
    return false
  }
}

// Componente Provedor
export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem("authToken")) // Ler token inicial
  const [user, setUser] = useState(null) // Armazenar dados do usuário (/users/me)
  const [isAuthenticated, setIsAuthenticated] = useState(() => isTokenValid(localStorage.getItem("authToken")))
  const [loading, setLoading] = useState(false) // Para feedback de loading no login/fetch user
  const [error, setError] = useState(null) // Para erros de login/fetch user
  const navigate = useNavigate()

  // Função para buscar dados do usuário (/users/me)
  const fetchUser = useCallback(async () => {
    const currentToken = localStorage.getItem("authToken")
    if (!currentToken || !isTokenValid(currentToken)) {
      console.log("fetchUser: No valid token found, skipping fetch.")
      setIsAuthenticated(false)
      setUser(null)
      setToken(null) // Ensure state consistency
      return
    }

    console.log("fetchUser: Valid token found, attempting to fetch user data...")
    setLoading(true)
    setError(null)
    try {
      // O interceptor do apiClient já adicionará o token
      const response = await apiClient.get("/users/me")
      setUser(response.data)
      setIsAuthenticated(true)
      setToken(currentToken) // Update state token if needed
      console.log("User data fetched successfully:", response.data)
    } catch (err) {
      console.error("Erro ao buscar dados do usuário (/users/me):", err.message)
      setError(err.message || "Falha ao carregar dados do usuário.")
      // Token pode ser válido mas /users/me falhou (ex: user deletado), deslogar
      localStorage.removeItem("authToken")
      setToken(null)
      setUser(null)
      setIsAuthenticated(false)
    } finally {
      setLoading(false)
    }
  }, [])

  // Efeito para buscar usuário ao carregar ou quando token mudar (externamente)
  // This might cause loops if not careful. Only fetch on initial load with valid token.
  useEffect(() => {
    const initialToken = localStorage.getItem("authToken")
    if (isTokenValid(initialToken) && !user) {
      // Only fetch if token valid and user not loaded
      console.log("Initial load: Fetching user data...")
      fetchUser()
    } else if (!isTokenValid(initialToken)) {
      // Clean up state if initial token is invalid/missing
      setUser(null)
      setToken(null)
      setIsAuthenticated(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Run only once on mount

  // Função de Login
  const login = useCallback(
    async (username, password) => {
      setLoading(true)
      setError(null)
      setUser(null) // Clear previous user data
      setIsAuthenticated(false)
      setToken(null)
      localStorage.removeItem("authToken") // Clear old token first

      try {
        // Usar URLSearchParams para form data como esperado pelo backend OAuth2
        const formData = new URLSearchParams()
        formData.append("username", username) // FastAPI espera 'username'
        formData.append("password", password)

        const response = await apiClient.post("/auth/login", formData, {
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        })

        const newAuthToken = response.data.access_token
        console.log("Login successful, received token:", newAuthToken)

        // Salvar token e atualizar estado
        localStorage.setItem("authToken", newAuthToken)
        setToken(newAuthToken)
        setIsAuthenticated(true)

        // Buscar dados do usuário após login bem-sucedido
        await fetchUser() // Fetch user immediately after getting token

        // Navegar para a página principal (ex: /comms)
        navigate("/comms") // Ou para a última página visitada
      } catch (err) {
        console.error("Erro durante o login:", err.message)
        const loginError = err.message || "Falha no login. Verifique suas credenciais."
        setError(loginError)
        // Garantir limpeza do estado em caso de falha
        localStorage.removeItem("authToken")
        setToken(null)
        setUser(null)
        setIsAuthenticated(false)
        // Re-throw error so login form can display it? Optional.
        // throw new Error(loginError);
      } finally {
        setLoading(false)
      }
    },
    [fetchUser, navigate],
  )

  // Função de Logout
  const logout = useCallback(() => {
    console.log("Executando logout...")
    setUser(null)
    setToken(null)
    setIsAuthenticated(false)
    setError(null)
    localStorage.removeItem("authToken")
    // Opcional: Limpar outros caches/estados relacionados ao usuário
    navigate("/login") // Redirecionar para login
  }, [navigate])

  // --- Event Listener para erro 401 global ---
  useEffect(() => {
    const handleAuthError = () => {
      console.warn("AuthContext received 'auth-error-401' event. Logging out.")
      // Chamar logout SOMENTE se usuário ainda estiver marcado como autenticado
      // para evitar loops se o erro 401 ocorrer na página de login
      if (isAuthenticated) {
        logout()
      }
    }

    window.addEventListener("auth-error-401", handleAuthError)
    console.log("AuthContext: Event listener for 'auth-error-401' added.")

    // Cleanup: remover listener ao desmontar
    return () => {
      window.removeEventListener("auth-error-401", handleAuthError)
      console.log("AuthContext: Event listener for 'auth-error-401' removed.")
    }
  }, [logout, isAuthenticated]) // Adicionar isAuthenticated à dependência

  // Valor fornecido pelo Contexto
  const contextValue = {
    token,
    user,
    isAuthenticated,
    loading,
    error,
    login,
    logout,
    fetchUser, // Expor fetchUser se necessário recarregar manualmente
  }

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
}

// Hook customizado para consumir o contexto (será criado em useAuth.js)
// export const useAuth = () => useContext(AuthContext);

// Exportar o Contexto diretamente para ser usado no hook useAuth.js
export default AuthContext
