"use client"

import { useContext } from "react"
import AuthContext from "../context/AuthContext" // Importar o contexto

/**
 * Hook customizado para acessar facilmente os dados e funções do AuthContext.
 * Levanta um erro se usado fora de um AuthProvider.
 */
export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === null) {
    // null é o valor inicial definido em createContext, se usado fora do Provider
    throw new Error("useAuth must be used within an AuthProvider")
  }
  // Se context for undefined, também é um erro (embora menos provável com o check de null)
  if (context === undefined) {
    throw new Error("AuthContext returned undefined. Check AuthProvider setup.")
  }
  return context
}
