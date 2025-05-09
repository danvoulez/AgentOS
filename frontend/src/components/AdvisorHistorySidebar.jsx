"use client"

import { useState, useEffect, forwardRef, useImperativeHandle } from "react"
import { useAuth } from "../hooks/useAuth"
import apiClient from "../services/api"
import LoadingSpinner from "./LoadingSpinner"
import { PlusIcon, ArrowPathIcon, ChevronLeftIcon, ChevronRightIcon } from "@heroicons/react/24/outline"

/**
 * Componente de barra lateral para exibir o histórico de conversas do Advisor.
 * Permite selecionar conversas existentes e iniciar novas.
 */
const AdvisorHistorySidebar = forwardRef(
  ({ currentConversationId, onSelectConversation, onNewConversation, isLoading }, ref) => {
    const [conversations, setConversations] = useState([])
    const [isHistoryLoading, setIsHistoryLoading] = useState(false)
    const [error, setError] = useState(null)
    const [isCollapsed, setIsCollapsed] = useState(false)
    const { user } = useAuth()

    // Função para buscar histórico de conversas
    const fetchConversationHistory = async () => {
      if (!user?.id) return

      setIsHistoryLoading(true)
      setError(null)

      try {
        const response = await apiClient.get("/advisor/conversations")
        setConversations(response.data || [])
      } catch (err) {
        console.error("Erro ao buscar histórico de conversas:", err)
        setError("Falha ao carregar histórico de conversas")
      } finally {
        setIsHistoryLoading(false)
      }
    }

    // Expor função de atualização para componente pai
    useImperativeHandle(ref, () => ({
      refreshHistory: fetchConversationHistory,
    }))

    // Buscar histórico na montagem do componente
    useEffect(() => {
      fetchConversationHistory()
    }, [user?.id])

    // Formatar data para exibição
    const formatDate = (dateString) => {
      if (!dateString) return ""

      const date = new Date(dateString)
      const now = new Date()
      const yesterday = new Date(now)
      yesterday.setDate(yesterday.getDate() - 1)

      // Se for hoje, mostrar apenas a hora
      if (date.toDateString() === now.toDateString()) {
        return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      }

      // Se for ontem, mostrar "Ontem"
      if (date.toDateString() === yesterday.toDateString()) {
        return "Ontem"
      }

      // Caso contrário, mostrar data
      return date.toLocaleDateString()
    }

    return (
      <>
        <div
          className={`relative h-full bg-fusion-dark border-r border-fusion-medium transition-all duration-300 ${
            isCollapsed ? "w-12" : "w-64 md:w-80"
          }`}
        >
          {/* Botão para colapsar/expandir */}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="absolute -right-3 top-20 bg-fusion-medium text-fusion-light rounded-full p-1 z-10 shadow-md"
            aria-label={isCollapsed ? "Expandir barra lateral" : "Colapsar barra lateral"}
          >
            {isCollapsed ? <ChevronRightIcon className="w-4 h-4" /> : <ChevronLeftIcon className="w-4 h-4" />}
          </button>

          {/* Cabeçalho */}
          <div className="p-4 border-b border-fusion-medium flex items-center justify-between">
            {!isCollapsed && <h2 className="text-lg font-semibold text-fusion-text-primary">Conversas</h2>}
            <div className="flex items-center space-x-2">
              <button
                onClick={onNewConversation}
                disabled={isLoading}
                className={`p-2 rounded-md bg-fusion-medium/40 hover:bg-fusion-medium text-fusion-text-primary transition-colors ${
                  isLoading ? "opacity-50 cursor-not-allowed" : ""
                }`}
                title="Nova conversa"
              >
                <PlusIcon className="w-5 h-5" />
              </button>

              {!isCollapsed && (
                <button
                  onClick={fetchConversationHistory}
                  disabled={isHistoryLoading || isLoading}
                  className={`p-2 rounded-md bg-fusion-medium/40 hover:bg-fusion-medium text-fusion-text-primary transition-colors ${
                    isHistoryLoading || isLoading ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                  title="Atualizar histórico"
                >
                  <ArrowPathIcon className={`w-5 h-5 ${isHistoryLoading ? "animate-spin" : ""}`} />
                </button>
              )}
            </div>
          </div>

          {/* Lista de conversas */}
          <div className="overflow-y-auto h-[calc(100%-60px)] scrollbar">
            {isHistoryLoading ? (
              <div className="flex flex-col items-center justify-center p-8">
                <LoadingSpinner />
                {!isCollapsed && <p className="text-sm text-fusion-light mt-2">Carregando conversas...</p>}
              </div>
            ) : error ? (
              <div className="p-4 text-center">
                {!isCollapsed && <p className="text-sm text-fusion-error">{error}</p>}
              </div>
            ) : conversations.length === 0 ? (
              <div className="p-4 text-center">
                {!isCollapsed && <p className="text-sm text-fusion-light">Nenhuma conversa encontrada</p>}
              </div>
            ) : (
              <ul className="divide-y divide-fusion-medium/30">
                {conversations.map((conversation) => (
                  <li key={conversation.id}>
                    <button
                      onClick={() => onSelectConversation(conversation.id)}
                      disabled={isLoading || conversation.id === currentConversationId}
                      className={`w-full text-left p-3 hover:bg-fusion-medium/20 transition-colors ${
                        conversation.id === currentConversationId ? "bg-fusion-medium/30 font-medium" : ""
                      } ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
                    >
                      {isCollapsed ? (
                        <div className="flex justify-center">
                          <span className="w-2 h-2 rounded-full bg-fusion-purple"></span>
                        </div>
                      ) : (
                        <>
                          <div className="truncate text-sm text-fusion-text-primary">
                            {conversation.title || "Conversa sem título"}
                          </div>
                          <div className="flex justify-between items-center mt-1">
                            <span className="text-xs text-fusion-light">
                              {formatDate(conversation.updated_at || conversation.created_at)}
                            </span>
                            <span className="text-xs text-fusion-light">{conversation.message_count || 0} msgs</span>
                          </div>
                        </>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </>
    )
  },
)

AdvisorHistorySidebar.displayName = "AdvisorHistorySidebar"

export default AdvisorHistorySidebar
