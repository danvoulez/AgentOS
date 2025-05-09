"use client"

import { createContext, useState, useEffect, useCallback, useContext } from "react"
import apiClient from "../services/api"

// Create the context with a default value of null
const AuthContext = createContext(null)

/**
 * Provider component for authentication state and functions.
 * Manages user authentication state, login, logout, and token refresh.
 */
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Check if user is authenticated on initial load
  useEffect(() => {
    const checkAuthStatus = async () => {
      const token = localStorage.getItem("authToken")
      if (!token) {
        setLoading(false)
        return
      }

      try {
        // Set the token in the API client
        apiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`

        // Get user info
        const response = await apiClient.get("/auth/me")
        setUser(response.data)
      } catch (err) {
        console.error("Auth check failed:", err)
        // Clear invalid token
        localStorage.removeItem("authToken")
        delete apiClient.defaults.headers.common["Authorization"]
      } finally {
        setLoading(false)
      }
    }

    checkAuthStatus()
  }, [])

  // Login function
  const login = useCallback(async (email, password) => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.post("/auth/login", { email, password })
      const { access_token, user: userData } = response.data

      // Store token and set in API client
      localStorage.setItem("authToken", access_token)
      apiClient.defaults.headers.common["Authorization"] = `Bearer ${access_token}`

      setUser(userData)
      return userData
    } catch (err) {
      console.error("Login failed:", err)
      const errorMessage = err.response?.data?.detail || "Login failed. Please check your credentials."
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  // Logout function
  const logout = useCallback(() => {
    localStorage.removeItem("authToken")
    delete apiClient.defaults.headers.common["Authorization"]
    setUser(null)
  }, [])

  // Value object to be provided to consumers
  const value = {
    user,
    isAuthenticated: !!user,
    loading,
    error,
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export default AuthContext

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
