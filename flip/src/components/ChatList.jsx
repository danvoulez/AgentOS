"use client"

// src/components/MessageView.jsx
import { useState, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import apiClient from "../services/api"
import { useWebSocket } from "../hooks/useWebSocket"
import LoadingSpinner from "./LoadingSpinner"
import { useScrollToBottom } from "../hooks/useScrollToBottom" // Import hook
import { format } from "date-fns" // For formatting timestamps
import { ptBR } from "date-fns/locale"
// Icons for message status/types
import {
  CheckIcon,
  ClockIcon,
  ExclamationCircleIcon,
  PaperClipIcon,
  MapPinIcon,
  PhotoIcon,
  MicrophoneIcon,
} from "@heroicons/react/24/outline"
import { CheckIcon as CheckIconSolid } from "@heroicons/react/24/solid" // For read status?
import { useAuth } from "../hooks/useAuth"

const logger = { info: console.log, error: console.error, warn: console.warn, debug: console.debug }

// Individual Message Component
function SingleMessage({ message, isOwnMessage }) {
  const { content, timestamp, status, type, sender_id, transcription } = message

  // Format timestamp
  let formattedTime = ""
  if (timestamp) {
    try {
      // Show HH:mm for today, dd/MM HH:mm for other days?
      const msgDate = new Date(timestamp)
      const today = new Date()
      if (msgDate.toDateString() === today.toDateString()) {
        formattedTime = format(msgDate, "HH:mm", { locale: ptBR })
      } else {
        formattedTime = format(msgDate, "dd/MM HH:mm", { locale: ptBR })
      }
    } catch (e) {
      logger.warn(`Could not format message timestamp: ${timestamp}`, e)
      formattedTime = "inválido"
    }
  }

  // Determine message bubble style based on sender
  const bubbleClasses = isOwnMessage
    ? "bg-fusion-purple text-white rounded-br-none" // Sent message style
    : "bg-fusion-dark text-fusion-text-primary rounded-bl-none" // Received message style

  // --- Status Icon Logic (for sent messages) ---
  const renderStatusIcon = () => {
    if (!isOwnMessage) return null
    switch (status) {
      case "pending_queue":
      case "pending_send":
        return <ClockIcon className="w-3 h-3 text-gray-400" title="Enviando..." />
      case "sent":
        return <CheckIcon className="w-3.5 h-3.5 text-gray-400" title="Enviado" />
      case "delivered":
        // Use two checks? Or a specific icon?
        return <CheckIconSolid className="w-3.5 h-3.5 text-fusion-blue" title="Entregue" /> // Example blue
      case "read":
        // Use two solid checks?
        return <CheckIconSolid className="w-3.5 h-3.5 text-fusion-teal" title="Lido" /> // Example teal
      case "failed_send":
      case "agent_error":
      case "failed_system":
        return <ExclamationCircleIcon className="w-3.5 h-3.5 text-fusion-error" title={`Falha: ${status}`} />
      default:
        return null // Unknown status
    }
  }

  // --- Render Content based on Type ---
  const renderContent = () => {
    switch (type) {
      case "text":
      case "text_agent": // Treat agent text same as normal text for now
      case "text_auto_response":
        return <p className="whitespace-pre-wrap break-words">{content || ""}</p>
      case "audio":
        return (
          <div className="flex items-center space-x-2">
            <MicrophoneIcon className="w-5 h-5 text-fusion-light" />
            <span>Áudio {content ? `(${content})` : ""}</span>
            {/* Display transcription if available */}
            {transcription && (
              <p className="mt-1 text-xs italic text-gray-400 w-full border-t border-gray-600 pt-1">
                "{transcription}"
              </p>
            )}
            {/* TODO: Add audio player? Requires media download logic */}
          </div>
        )
      case "image":
        return (
          <div className="flex items-center space-x-2">
            <PhotoIcon className="w-5 h-5 text-fusion-light" />
            <span>Imagem {content ? `- ${content}` : ""}</span>
            {/* TODO: Display thumbnail/image? Requires media download */}
          </div>
        )
      case "document":
        return (
          <div className="flex items-center space-x-2">
            <PaperClipIcon className="w-5 h-5 text-fusion-light" />
            <span>Documento {content ? `- ${content}` : ""}</span>
            {/* TODO: Add download link? Requires media info */}
          </div>
        )
      case "location":
        // Content might be pre-formatted, or use metadata
        return (
          <div className="flex items-center space-x-2">
            <MapPinIcon className="w-5 h-5 text-fusion-light" />
            <span>{content || "Localização"}</span>
            {/* TODO: Display map link? */}
          </div>
        )
      // Add cases for video, sticker, contacts, reaction, etc.
      default:
        return (
          <p className="text-xs italic text-fusion-light">
            [Tipo de mensagem não suportado: {type}] {content || ""}
          </p>
        )
    }
  }

  const messageVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.2 } },
  }

  return (
    <motion.div
      layout
      variants={messageVariants}
      initial="hidden"
      animate="visible"
      className={`flex mb-2 ${isOwnMessage ? "justify-end" : "justify-start"}`}
    >
      <div className={`px-3 py-2 rounded-lg max-w-[75%] shadow ${bubbleClasses}`}>
        {/* Render sender name if group chat? (Not applicable for 1-on-1 WA) */}
        <div className="text-sm">{renderContent()}</div>
        <div
          className={`text-[10px] mt-1 flex items-center space-x-1 ${isOwnMessage ? "justify-end text-blue-100/80" : "justify-start text-gray-400"}`}
        >
          <span>{formattedTime}</span>
          {renderStatusIcon()}
        </div>
      </div>
    </motion.div>
  )
}
// import { motion, AnimatePresence } from "framer-motion" // Removed duplicated import
// import { useScrollToBottom } from "../hooks/useScrollToBottom" // Removed duplicated import

/**
 * Componente para renderizar uma lista de mensagens de chat com animações.
 * @param {Object[]} messages - Array de objetos de mensagem
 * @param {string} userId - ID do usuário atual para determinar alinhamento
 * @param {Function} renderMessage - Função para renderizar cada mensagem
 * @param {boolean} isLoading - Indica se está carregando mais mensagens
 * @param {React.ReactNode} loadingIndicator - Componente de indicador de carregamento
 * @param {React.ReactNode} emptyState - Componente para estado vazio
 */
const ChatList = ({ messages = [], userId, renderMessage, isLoading = false, loadingIndicator, emptyState }) => {
  // Hook para rolar para o final quando novas mensagens são adicionadas
  const scrollContainerRef = useScrollToBottom(messages)

  // Verificar se há mensagens para exibir
  const hasMessages = messages && messages.length > 0

  return (
    <div ref={scrollContainerRef} className="flex-grow overflow-y-auto p-4 md:p-6 space-y-4 scrollbar">
      {/* Estado de carregamento */}
      {isLoading && loadingIndicator}

      {/* Estado vazio */}
      {!isLoading && !hasMessages && emptyState}

      {/* Lista de mensagens com animações */}
      <AnimatePresence initial={false}>
        {hasMessages &&
          messages.map((message, index) => (
            <motion.div
              key={message.id || `msg-${index}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              {renderMessage(message, index)}
            </motion.div>
          ))}
      </AnimatePresence>
    </div>
  )
}

// Main Message View Component
function MessageView({ chatId }) {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const { lastJsonMessage } = useWebSocket()
  const { user } = useAuth() // Get current user to determine 'isOwnMessage'

  const messagesContainerRef = useScrollToBottom(messages) // Auto-scroll hook

  // Fetch messages when chatId changes
  const fetchMessages = useCallback(async (id) => {
    if (!id) {
      setMessages([]) // Clear messages if no chat is selected
      setError(null)
      setIsLoading(false)
      return
    }
    setIsLoading(true)
    setError(null)
    logger.info(`Fetching messages for chat ID: ${id}`)
    try {
      // Assume API returns messages sorted oldest to newest
      const response = await apiClient.get(`/whatsapp/chats/${id}/messages`, { params: { limit: 100 } }) // Add pagination later
      setMessages(response.data || [])
    } catch (err) {
      logger.error(`Error fetching messages for chat ${id}:`, err)
      setError("Falha ao carregar mensagens.")
      setMessages([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMessages(chatId)
  }, [chatId, fetchMessages])

  // Handle WebSocket updates for new messages or status changes in THIS chat
  useEffect(() => {
    if (!lastJsonMessage || !chatId) return // Only process if a chat is selected

    const { type, payload } = lastJsonMessage

    // New message FOR THIS CHAT
    if (type === "new_whatsapp_message" && payload && payload.chat_id === chatId) {
      logger.debug(`WS: new_whatsapp_message for current chat ${chatId}`, payload)
      setMessages((prev) => {
        // Avoid adding duplicates if message already exists by ID
        if (prev.some((msg) => msg.id === payload.id)) return prev
        // Validate with API model? Or assume payload matches
        // const apiMessage = WhatsAppMessageAPI.model_validate(payload);
        return [...prev, payload] // Add the new message
      })
      // TODO: Optionally mark as read if window is focused?
    }
    // Message status update FOR A MESSAGE IN THIS CHAT
    else if (type === "whatsapp_message_status" && payload && payload.chat_id === chatId) {
      logger.debug(`WS: whatsapp_message_status for current chat ${chatId}`, payload)
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === payload.id ? { ...msg, status: payload.status, status_timestamp: payload.timestamp } : msg,
        ),
      )
    }
  }, [lastJsonMessage, chatId])

  return (
    // Use theme colors
    <div ref={messagesContainerRef} className="flex-grow overflow-y-auto p-4 md:p-6 space-y-1 bg-fusion-deep scrollbar">
      {" "}
      {/* Apply scrollbar, maybe different bg? */}
      {isLoading && (
        <div className="text-center py-10">
          <LoadingSpinner />
        </div>
      )}
      {!isLoading && error && <p className="text-center text-fusion-error text-sm py-10">{error}</p>}
      {!isLoading && !error && messages.length === 0 && chatId && (
        <p className="text-center text-fusion-light text-sm py-10 italic">Nenhuma mensagem nesta conversa ainda.</p>
      )}
      {!isLoading && !error && !chatId && (
        <p className="text-center text-fusion-light text-sm py-10 italic">
          Selecione uma conversa para ver as mensagens.
        </p>
      )}
      {!isLoading && !error && messages.length > 0 && (
        <AnimatePresence initial={false}>
          {messages.map((msg) => {
            // Determine if the message is from the logged-in user (employee/agent)
            const isOwn =
              msg.sender_id?.startsWith("employee:") || msg.sender_id === "agent" || msg.sender_id === "auto_responder"
            // const isOwn = msg.sender_id === user?.email; // Simpler if sender_id is always email for employees
            return (
              <SingleMessage
                key={msg.id || `msg-${Math.random()}`} // Use unique ID
                message={msg}
                isOwnMessage={isOwn}
              />
            )
          })}
        </AnimatePresence>
      )}
    </div>
  )
}

export default MessageView
