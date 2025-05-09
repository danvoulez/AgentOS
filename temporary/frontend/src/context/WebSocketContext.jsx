"use client"

import { createContext, useState, useEffect, useCallback, useRef, useContext } from "react"
import { useAuth } from "../hooks/useAuth"

// Create the context with a default value of null
const WebSocketContext = createContext(null)

/**
 * Provider component for WebSocket connection and related state.
 * Manages WebSocket connection, reconnection, and message handling.
 */
export const WebSocketProvider = ({ children }) => {
  const { user, isAuthenticated } = useAuth()
  const [isConnected, setIsConnected] = useState(false)
  const [messages, setMessages] = useState([])
  const [error, setError] = useState(null)

  // Use a ref for the WebSocket to persist across renders
  const wsRef = useRef(null)

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!isAuthenticated || !user?.id) {
      console.log("Not connecting WebSocket: user not authenticated")
      return
    }

    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close()
    }

    try {
      // Get the WebSocket URL from environment or use default
      const wsUrl = import.meta.env.VITE_WS_URL || "ws://localhost:8000"
      const token = localStorage.getItem("authToken")

      // Create WebSocket connection with authentication
      const ws = new WebSocket(`${wsUrl}/ws/${user.id}?token=${token}`)
      wsRef.current = ws

      // WebSocket event handlers
      ws.onopen = () => {
        console.log("WebSocket connected")
        setIsConnected(true)
        setError(null)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log("WebSocket message received:", data)
          setMessages((prev) => [...prev, data])
        } catch (err) {
          console.error("Error parsing WebSocket message:", err)
        }
      }

      ws.onerror = (event) => {
        console.error("WebSocket error:", event)
        setError("WebSocket connection error")
        setIsConnected(false)
      }

      ws.onclose = (event) => {
        console.log("WebSocket disconnected:", event)
        setIsConnected(false)

        // Attempt to reconnect after delay if not closed cleanly
        if (event.code !== 1000) {
          setTimeout(() => connect(), 3000)
        }
      }
    } catch (err) {
      console.error("Error creating WebSocket:", err)
      setError("Failed to create WebSocket connection")
    }
  }, [isAuthenticated, user?.id])

  // Connect when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      connect()
    }

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [isAuthenticated, connect])

  // Send message through WebSocket
  const sendMessage = useCallback((message) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError("WebSocket not connected")
      return false
    }

    try {
      wsRef.current.send(JSON.stringify(message))
      return true
    } catch (err) {
      console.error("Error sending WebSocket message:", err)
      setError("Failed to send message")
      return false
    }
  }, [])

  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  // Value object to be provided to consumers
  const value = {
    isConnected,
    messages,
    error,
    sendMessage,
    clearMessages,
    connect,
  }

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>
}

export default WebSocketContext

export const useWebSocket = () => {
  const context = useContext(WebSocketContext)
  if (context === null) {
    throw new Error("useWebSocket must be used within a WebSocketProvider")
  }
  return context
}
