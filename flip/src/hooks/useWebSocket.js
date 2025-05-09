"use client"

import { useContext } from "react"
import WebSocketContext from "../context/WebSocketContext" // Correct import path

/**
 * Hook customizado para acessar facilmente os dados e funções do WebSocketContext.
 * Levanta um erro se usado fora de um WebSocketProvider.
 */
export const useWebSocket = () => {
  const context = useContext(WebSocketContext)
  if (context === null) {
    throw new Error("useWebSocket must be used within a WebSocketProvider")
  }
  if (context === undefined) {
    throw new Error("WebSocketContext returned undefined. Check WebSocketProvider setup.")
  }
  return context
}
