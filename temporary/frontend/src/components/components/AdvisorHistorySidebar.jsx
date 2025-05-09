"use client"

// src/components/AdvisorHistorySidebar.jsx
import { useState, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import apiClient from "../services/api"
import { useAuth } from "../context/AuthContext" // Para pegar user ID
import LoadingSpinner from "./LoadingSpinner"
import { formatDistanceToNow } from "date-fns" // Para datas relativas (npm install date-fns)
import { ptBR } from "date-fns/locale" // Para formato pt-BR
// Ícones (exemplo com Heroicons - npm install @heroicons/react)
import { PlusIcon, TrashIcon, ChatBubbleLeftEllipsisIcon } from "@heroicons/react/24/outline"

const logger = { info: console.log, error: console.error, warn: console.warn, debug: console.debug }

function ConversationItem({ conversation, isSelected, onSelect, onDelete }) {
  const updatedAt = conversation.updated_at ? new Date(conversation.updated_at) : new Date()
  // Handle potential invalid date strings gracefully
  let timeAgo = "há pouco"
  try {
    timeAgo = formatDistanceToNow(updatedAt, { addSuffix: true, locale: ptBR })
  } catch (e) {
    logger.warn(`Could not format date for conversation ${conversation.id}: ${conversation.updated_at}`, e)
  }

  const handleDeleteClick = (e) => {
    e.stopPropagation() // Impedir que o clique no botão selecione a conversa
    if (window.confirm(`Tem certeza que deseja deletar a conversa "${conversation.title}"?`)) {
      onDelete(conversation.id)
    }
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      onClick={() => onSelect(conversation.id)}
      // Use theme colors (replace 'purple-700/50', 'gray-700', etc. with 'vv-*' or 'fusion-*')
      className={`flex items-center justify-between p-2.5 rounded-md cursor-pointer transition-colors duration-150 group ${
        isSelected ? "bg-fusion-purple/50" : "hover:bg-fusion-medium" // Example theme colors
      }`}
    >
      <div className="flex items-center space-x-2 overflow-hidden">
        <ChatBubbleLeftEllipsisIcon className="w-4 h-4 text-fusion-light flex-shrink-0" /> {/* Theme color */}
        <span
          className={`text-sm truncate ${isSelected ? "text-fusion-text-primary font-medium" : "text-fusion-text-secondary"}`}
        >
          {" "}
          {/* Theme colors */}
          {conversation.title || "Conversa sem título"}
        </span>
      </div>
      <div className="flex items-center space-x-1 flex-shrink-0 pl-2">
        <span className="text-[10px] text-fusion-light group-hover:hidden">
          {" "}
          {/* Theme color */}
          {timeAgo}
        </span>
        {/* Botão de deletar aparece no hover ou se selecionado */}
        <button
          onClick={handleDeleteClick}
          title="Deletar conversa"
          // Use theme colors (red-500 -> fusion-error)
          className={`p-1 rounded text-fusion-light hover:text-fusion-error opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity ${isSelected ? "opacity-100" : ""}`}
        >
          <TrashIcon className="w-4 h-4" />
        </button>
      </div>
    </motion.div>
  )
}

function AdvisorHistorySidebar({ currentConversationId, onSelectConversation, onNewConversation, isLoading }) {
  const { token } = useAuth() // Assume useAuth provides token if needed for API calls via interceptor
  const [conversations, setConversations] = useState([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [error, setError] = useState(null)

  const fetchHistory = useCallback(async () => {
    // Token check might be handled by apiClient interceptor now
    // if (!token) return;
    setLoadingHistory(true)
    setError(null)
    try {
      // Adjust limit as needed
      const response = await apiClient.get("/advisor/conversations", { params: { limit: 100 } })
      // Sort by updated_at descending before setting state
      const sortedConversations = (response.data || []).sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
      setConversations(sortedConversations)
    } catch (err) {
      logger.error("Erro ao buscar histórico do Advisor:", err)
      setError("Falha ao carregar histórico.")
      setConversations([])
    } finally {
      setLoadingHistory(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Removed token dependency if interceptor handles it

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  const handleDelete = async (conversationId) => {
    if (isLoading) return // Não deletar enquanto outra operação está em andamento
    logger.info(`Deletando conversa ${conversationId}`)
    try {
      await apiClient.delete(`/advisor/conversations/${conversationId}`)
      setConversations((prev) => prev.filter((c) => c.id !== conversationId))
      // Se a conversa deletada era a ativa, iniciar uma nova
      if (currentConversationId === conversationId) {
        onNewConversation()
      }
      // Optionally refetch history after delete to ensure sync
      // fetchHistory();
    } catch (err) {
      logger.error(`Erro ao deletar conversa ${conversationId}:`, err)
      setError("Falha ao deletar conversa.") // Mostrar erro temporário?
      setTimeout(() => setError(null), 3000)
    }
  }

  // Function to manually trigger a refresh of the history list
  const refreshHistory = useCallback(() => {
    logger.debug("Refreshing Advisor history list manually...")
    fetchHistory()
  }, [fetchHistory])

  // TODO: Consider a way to trigger refresh from parent (AdvisorPage) when a new chat title is set
  // Maybe pass refreshHistory as a prop up? Or use a shared context/state manager.

  return (
    // Use theme colors (bg-gray-800 -> bg-fusion-dark, border-gray-700 -> border-fusion-medium)
    <div className="w-64 bg-fusion-dark h-full flex flex-col border-r border-fusion-medium">
      {/* Botão Nova Conversa */}
      <div className="p-3 border-b border-fusion-medium">
        <button
          onClick={onNewConversation}
          // Use theme colors (bg-purple-600 -> bg-fusion-purple, hover:bg-purple-700 -> hover:bg-fusion-purple-hover)
          className="w-full flex items-center justify-center space-x-2 px-3 py-2 rounded-md text-sm font-medium bg-fusion-purple hover:bg-fusion-purple-hover text-white transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-fusion-purple-light disabled:opacity-50"
          disabled={isLoading} // Disable if Advisor is thinking OR history is loading
        >
          <PlusIcon className="w-5 h-5" />
          <span>Nova Conversa</span>
        </button>
      </div>

      {/* Lista de Conversas */}
      {/* Apply custom scrollbar style if plugin is used */}
      <div className="flex-grow overflow-y-auto p-2 space-y-1 scrollbar scrollbar-thumb-fusion-purple/60 scrollbar-track-fusion-dark/50">
        {loadingHistory && (
          <div className="p-4 text-center">
            <LoadingSpinner />
          </div>
        )}
        {!loadingHistory && error && (
          <p className="p-4 text-center text-fusion-error text-xs">{error}</p> // Theme color
        )}
        {!loadingHistory && !error && conversations.length === 0 && (
          <p className="p-4 text-center text-fusion-light text-sm italic">Nenhuma conversa ainda.</p> // Theme color
        )}
        {/* AnimatePresence para animar itens da lista */}
        <AnimatePresence>
          {!loadingHistory &&
            !error &&
            conversations.map((conv) => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                isSelected={conv.id === currentConversationId}
                onSelect={onSelectConversation}
                onDelete={handleDelete}
              />
            ))}
        </AnimatePresence>
      </div>
      {/* Opcional: Botão de Refresh Manual */}
      <div className="p-2 border-t border-fusion-medium text-center">
        <button
          onClick={refreshHistory}
          className="text-xs text-fusion-light hover:text-fusion-text-primary"
          disabled={loadingHistory}
        >
          {loadingHistory ? "Carregando..." : "Atualizar Histórico"}
        </button>
      </div>
    </div>
  )
}

export default AdvisorHistorySidebar
