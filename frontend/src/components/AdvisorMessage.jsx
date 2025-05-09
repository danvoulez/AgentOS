"use client"
import { motion } from "framer-motion"
import StructuredDataRenderer from "./StructuredDataRenderer"
import MessageView from "./MessageView"

/**
 * Componente para renderizar uma mensagem do Advisor ou do usuário.
 * Suporta diferentes tipos de conteúdo (texto, dados estruturados) e emoções.
 * @param {Object} message - Objeto da mensagem com role, content, emotion, etc.
 * @param {Function} onFollowUpClick - Callback para quando um botão de follow-up é clicado.
 */
const AdvisorMessage = ({ message, onFollowUpClick }) => {
  const isUser = message.role === "user"
  const isAssistant = message.role === "assistant"

  // Determinar se o conteúdo é estruturado (objeto) ou texto
  const isStructuredData = isAssistant && typeof message.content === "object"

  // Animação para entrada de mensagens
  const messageVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
    exit: { opacity: 0, transition: { duration: 0.2 } },
  }

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      exit="exit"
      variants={messageVariants}
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}
    >
      <div
        className={`rounded-lg p-4 max-w-[85%] ${
          isUser ? "bg-fusion-purple/20 text-fusion-text-primary" : "bg-fusion-medium/40 text-fusion-text-primary"
        }`}
      >
        {isStructuredData ? (
          <StructuredDataRenderer data={message.content} />
        ) : (
          <MessageView content={message.content} emotion={message.emotion} />
        )}

        {/* Botões de follow-up actions, se existirem */}
        {isAssistant && message.follow_up_actions && message.follow_up_actions.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {message.follow_up_actions.map((action, index) => (
              <button
                key={index}
                onClick={() => onFollowUpClick(action)}
                className="px-3 py-1.5 text-sm bg-fusion-medium hover:bg-fusion-medium/80 text-fusion-text-primary rounded-full transition-colors"
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}

export default AdvisorMessage
