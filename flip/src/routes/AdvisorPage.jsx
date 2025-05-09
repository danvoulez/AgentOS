"use client"

import { useState, useRef, useCallback } from "react"
import { useAuth } from "../hooks/useAuth"
import apiClient from "../services/api"
import { useScrollToBottom } from "../hooks/useScrollToBottom"
import InputBar from "../components/InputBar"
import LoadingSpinner from "../components/LoadingSpinner"
import AdvisorMessage from "../components/AdvisorMessage"
import AdvisorHistorySidebar from "../components/AdvisorHistorySidebar"
import { AnimatePresence, motion } from "framer-motion"

const logger = { info: console.log, error: console.error, warn: console.warn, debug: console.debug }

function AdvisorPage() {
  const { user } = useAuth()
  const [messages, setMessages] = useState([])
  const [currentConversationId, setCurrentConversationId] = useState(null)
  const [currentConversationTitle, setCurrentConversationTitle] = useState("Advisor IA")
  const [draft, setDraft] = useState("")
  const [isLoading, setIsLoading] = useState(false) // Loading Advisor response
  const [isChatLoading, setIsChatLoading] = useState(false) // Loading conversation history
  const [error, setError] = useState(null)
  const messagesContainerRef = useScrollToBottom(messages)
  const historySidebarRef = useRef() // Ref to call refreshHistory

  const loadConversationMessages = useCallback(
    async (conversationId) => {
      if (!conversationId || !user) return
      logger.info(`Carregando mensagens para conversa: ${conversationId}`)
      setIsChatLoading(true)
      setError(null)
      setMessages([])
      try {
        const response = await apiClient.get(`/advisor/conversations/${conversationId}`)
        const conversationData = response.data
        setMessages(conversationData.messages || [])
        setCurrentConversationTitle(conversationData.title || "Conversa Advisor")
      } catch (err) {
        logger.error(`Erro ao buscar mensagens da conversa ${conversationId}:`, err)
        const errorMsg = err.response?.data?.detail || "Falha ao carregar histórico da conversa."
        setError(errorMsg)
        setCurrentConversationId(null)
        setCurrentConversationTitle("Advisor IA")
        setMessages([])
      } finally {
        setIsChatLoading(false)
      }
    },
    [user],
  )

  const handleSelectConversation = useCallback(
    (conversationId) => {
      if (conversationId === currentConversationId || isLoading || isChatLoading) return
      setError(null) // Clear previous errors
      setCurrentConversationId(conversationId)
      loadConversationMessages(conversationId)
    },
    [currentConversationId, loadConversationMessages, isLoading, isChatLoading],
  )

  const handleNewConversation = useCallback(() => {
    logger.info("Iniciando nova conversa no Advisor.")
    setCurrentConversationId(null)
    setMessages([])
    setError(null)
    setDraft("")
    setCurrentConversationTitle("Nova Conversa")
  }, [])

  const sendMessageToGateway = useCallback(
    async (textToSend, context = {}, isFollowUp = false) => {
      if (!textToSend?.trim() || isLoading || isChatLoading || !user?.id) return

      const tempUserMessageId = `user-${Date.now()}`
      if (!isFollowUp) {
        const userMessage = { role: "user", content: textToSend, id: tempUserMessageId }
        setMessages((prev) => [...prev, userMessage])
      }

      setDraft("")
      setIsLoading(true)
      setError(null)

      const payload = {
        conversation_id: currentConversationId,
        user_id: user.id,
        request_type: "natural_language",
        payload: { text: textToSend },
        context: context,
      }

      if (context?.request_type === "structured") {
        payload.request_type = "structured"
        payload.payload = context.payload
      }

      logger.debug("Enviando para Gateway:", payload)
      let newConversationCreatedOrUpdated = false

      try {
        const response = await apiClient.post("/gateway/process", payload)
        const gatewayResponse = response.data
        logger.debug("Resposta do Gateway:", gatewayResponse)

        const newConversationId = gatewayResponse.conversation_id
        if (newConversationId && newConversationId !== currentConversationId) {
          logger.info(`Nova conversa iniciada/atualizada para ID: ${newConversationId}`)
          setCurrentConversationId(newConversationId)
          newConversationCreatedOrUpdated = true
          if (!isFollowUp && messages.length <= 1) {
            setCurrentConversationTitle(textToSend.substring(0, 40) + (textToSend.length > 40 ? "..." : ""))
          } else if (gatewayResponse.title) {
            setCurrentConversationTitle(gatewayResponse.title)
          }
        } else if (gatewayResponse.title && gatewayResponse.title !== currentConversationTitle) {
          setCurrentConversationTitle(gatewayResponse.title)
          newConversationCreatedOrUpdated = true
        }

        let aiMessageContent = null
        const followUps = gatewayResponse.follow_up_actions || null
        const explanation = gatewayResponse.explanation || null
        let emotion = gatewayResponse.suggested_emotion || "neutral"
        const tempAssistantMessageId = `assistant-${Date.now()}`

        if (gatewayResponse.response_type === "natural_language_text") {
          aiMessageContent = gatewayResponse.payload.text || "[Resposta vazia]"
        } else if (gatewayResponse.response_type === "structured_data") {
          aiMessageContent = gatewayResponse.payload.data ?? "[Dados estruturados vazios]"
        } else if (gatewayResponse.response_type === "error_message") {
          aiMessageContent = `⚠️ **Erro:** ${gatewayResponse.payload.message || "Erro desconhecido"}`
          if (gatewayResponse.payload.details) {
            aiMessageContent += `\n\`\`\`\n${gatewayResponse.payload.details}\n\`\`\``
          }
          emotion = "error_empathetic"
          setError(gatewayResponse.payload.message || "Erro no processamento do Advisor.")
        } else {
          aiMessageContent = "[Resposta inesperada do Advisor]"
          emotion = "confused"
          setError("Tipo de resposta desconhecido do Advisor.")
        }

        if (explanation && typeof aiMessageContent === "string") {
          aiMessageContent += "\n\n---\n*Explicação:*\n> " + explanation.join("\n> ")
        }

        const aiMessage = {
          role: "assistant",
          content: aiMessageContent,
          follow_up_actions: followUps,
          emotion: emotion,
          id: tempAssistantMessageId,
        }
        setMessages((prev) => [...prev, aiMessage])

        if (newConversationCreatedOrUpdated && historySidebarRef.current?.refreshHistory) {
          logger.debug("Triggering Advisor history refresh after new/updated conversation...")
          setTimeout(() => historySidebarRef.current.refreshHistory(), 500) // Delay might help backend consistency
        }
      } catch (err) {
        logger.error("Erro na chamada para /gateway/process:", err)
        const errorMsg = err.response?.data?.detail || err.message || "Falha ao se comunicar com o Advisor."
        setError(errorMsg)
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `⚠️ Ocorreu um erro ao processar sua solicitação:\n${errorMsg}`,
            emotion: "error",
            id: `error-${Date.now()}`,
          },
        ])
      } finally {
        setIsLoading(false)
      }
      // eslint-disable-next-line react-hooks/exhaustive-deps
    },
    [user, isLoading, isChatLoading, currentConversationId, messages.length, currentConversationTitle],
  )

  const handleSend = useCallback(() => {
    sendMessageToGateway(draft)
  }, [draft, sendMessageToGateway])

  const handleFollowUpClick = useCallback(
    (action) => {
      logger.debug("Follow-up action clicked:", action)
      sendMessageToGateway(action.label, { follow_up_origin: action }, true)
    },
    [sendMessageToGateway],
  )

  return (
    <div className="flex h-full w-full bg-fusion-deep">
      <AdvisorHistorySidebar
        ref={historySidebarRef}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        isLoading={isLoading || isChatLoading}
      />

      <div className="flex flex-col flex-1 h-full overflow-hidden">
        <div className="p-4 border-b border-fusion-medium bg-fusion-dark sticky top-0 z-10 flex justify-between items-center min-h-[60px]">
          {" "}
          {/* Ensure min height */}
          <h2 className="text-lg font-semibold text-fusion-text-primary truncate mr-4" title={currentConversationTitle}>
            {currentConversationTitle}
          </h2>
          {/* Maybe add a status indicator here if specific chat is loading? */}
        </div>

        <div ref={messagesContainerRef} className="flex-grow overflow-y-auto p-4 md:p-6 space-y-4 scrollbar">
          {isChatLoading && (
            <div className="text-center p-10">
              {" "}
              <LoadingSpinner /> <p className="text-sm text-fusion-light mt-2">Carregando conversa...</p>{" "}
            </div>
          )}

          {!isChatLoading && messages.length === 0 && !isLoading && (
            <p className="text-center text-fusion-light mt-10">
              Inicie uma nova conversa ou selecione uma no histórico.
            </p>
          )}

          <AnimatePresence initial={false}>
            {!isChatLoading &&
              messages.map((msg) => (
                <AdvisorMessage
                  key={msg.id || `msg-${Math.random()}`}
                  message={msg}
                  onFollowUpClick={handleFollowUpClick}
                />
              ))}
          </AnimatePresence>

          {isLoading && !isChatLoading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center justify-start py-4 space-x-2 text-fusion-light"
            >
              <LoadingSpinner /> <span>Pensando...</span>
            </motion.div>
          )}

          {/* Display general page error if not loading */}
          {error && !isLoading && !isChatLoading && (
            <div className="p-4 rounded-md bg-fusion-error/20 border border-fusion-error/50 text-fusion-error text-sm text-center">
              {error}
            </div>
          )}
        </div>

        <div className="sticky bottom-0 left-0 right-0 bg-fusion-deep border-t border-fusion-medium">
          <InputBar
            draft={draft}
            setDraft={setDraft}
            sendAction={handleSend}
            placeholder="Pergunte ao Advisor..."
            disabled={isLoading || isChatLoading}
          />
        </div>
      </div>
    </div>
  )
}

export default AdvisorPage
