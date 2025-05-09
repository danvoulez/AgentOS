"use client"

// src/components/RightHintsPanel.jsx
import { useState, useEffect, useCallback } from "react"
import { useWebSocket } from "../hooks/useWebSocket"
import { motion, AnimatePresence } from "framer-motion"
import { useNavigate } from "react-router-dom"
import { formatDistanceToNow } from "date-fns"
import { ptBR } from "date-fns/locale"
// Use solid icons for better visibility on dark backgrounds? Or adjust colors.
// Using outline for consistency for now. Adjust icon colors in getHintStyle.
import {
  LightBulbIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  ArrowTopRightOnSquareIcon,
  XMarkIcon,
  ChevronRightIcon,
  ChevronLeftIcon,
} from "@heroicons/react/24/outline"
import { v4 as uuidv4 } from "uuid"

const logger = { info: console.log, error: console.error, warn: console.warn, debug: console.debug }

// Function to map hint type to icon and Tailwind classes
const getHintStyle = (type) => {
  switch (type?.toLowerCase()) {
    case "alert": // Critical action needed
      return {
        icon: <ExclamationTriangleIcon className="w-5 h-5 text-fusion-error" />,
        bg: "bg-red-800/60 hover:bg-red-700/70 border-red-600/50",
      } // Use fusion-error theme color
    case "warning": // Potential issue
      return {
        icon: <ExclamationTriangleIcon className="w-5 h-5 text-fusion-warning" />,
        bg: "bg-yellow-700/60 hover:bg-yellow-600/70 border-yellow-600/50",
      } // Use fusion-warning
    case "suggestion": // Proactive suggestion
      return {
        icon: <LightBulbIcon className="w-5 h-5 text-fusion-purple-light" />,
        bg: "bg-purple-800/50 hover:bg-purple-700/60 border-purple-600/40",
      } // Use fusion-purple-light
    case "info": // General information
      return {
        icon: <InformationCircleIcon className="w-5 h-5 text-fusion-blue" />,
        bg: "bg-blue-800/50 hover:bg-blue-700/60 border-blue-600/40",
      } // Use fusion-blue
    case "success": // Confirmation
      return {
        icon: <CheckCircleIcon className="w-5 h-5 text-fusion-success" />,
        bg: "bg-green-800/50 hover:bg-green-700/60 border-green-600/40",
      } // Use fusion-success
    default: // Default/Unknown
      return {
        icon: <InformationCircleIcon className="w-5 h-5 text-fusion-light" />,
        bg: "bg-fusion-medium/50 hover:bg-fusion-medium/70 border-fusion-light/30",
      } // Use theme grays
  }
}

// Hint Card Component (extracted logic from previous RightHintsPanel)
function HintCard({ hint, onAction, onDismiss }) {
  const { icon, bg } = getHintStyle(hint.type)

  const cardVariants = {
    initial: { opacity: 0, x: 50, scale: 0.95 },
    animate: { opacity: 1, x: 0, scale: 1, transition: { duration: 0.3, ease: "easeOut" } },
    exit: { opacity: 0, x: -50, scale: 0.95, transition: { duration: 0.2, ease: "easeIn" } },
  }

  const updatedAt = hint.timestamp ? new Date(hint.timestamp) : new Date()
  let timeAgo = "agora"
  try {
    timeAgo = formatDistanceToNow(updatedAt, { addSuffix: true, locale: ptBR })
  } catch (e) {
    logger.warn("Hint date format error", e)
  }

  const handleActionClick = (e) => {
    e.stopPropagation() // Prevent potential parent clicks
    onAction(hint.action, hint.id) // Pass hint.id if needed for dismiss logic
  }

  const handleDismissClick = (e) => {
    e.stopPropagation()
    onDismiss(hint.id)
  }

  return (
    <motion.div
      layout // Animate layout changes (list reordering)
      variants={cardVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      // Use theme colors and add subtle border based on type
      className={`border p-3 rounded-lg shadow-lg mb-3 transition-colors duration-150 ${bg}`}
    >
      <div className="flex items-start space-x-3">
        <span className="mt-1 flex-shrink-0">{icon}</span> {/* Add flex-shrink-0 */}
        <div className="flex-grow min-w-0">
          {" "}
          {/* Allow text to wrap/truncate */}
          <p className="text-sm mb-1.5 text-fusion-text-primary break-words leading-snug">{hint.text}</p>
          {hint.action && (
            <button
              onClick={handleActionClick}
              // Use theme accent color
              className="inline-flex items-center space-x-1 text-xs text-fusion-purple-light hover:text-fusion-purple font-medium mt-1 transition-colors duration-150 focus:outline-none focus:ring-1 focus:ring-fusion-purple-light rounded px-1 py-0.5"
            >
              <span>{hint.action.label || "Detalhes"}</span>
              {/* Use different icon based on action type? Arrow for links, other for commands? */}
              <ArrowTopRightOnSquareIcon className="w-3 h-3" />
            </button>
          )}
          {/* Show timestamp relative */}
          <p className="text-[10px] text-fusion-light mt-1.5">{timeAgo}</p>
        </div>
        {/* Dismiss Button */}
        <button
          onClick={handleDismissClick}
          title="Dispensar Hint"
          // Use theme colors
          className="p-0.5 rounded-full text-fusion-light hover:text-fusion-error hover:bg-fusion-medium/50 transition-colors duration-150 flex-shrink-0 ml-1" // Added ml-1
        >
          <XMarkIcon className="w-4 h-4" />
        </button>
      </div>
    </motion.div>
  )
}

// Main Panel Component
/**
 * Componente de painel lateral direito para exibir dicas e informações adicionais.
 * @param {Object} props - Propriedades do componente
 * @param {React.ReactNode} props.children - Conteúdo do painel
 * @param {string} props.title - Título do painel
 */
const RightHintsPanel = ({ children, title = "Dicas & Informações" }) => {
  const { lastJsonMessage, isConnected, error: wsError } = useWebSocket()
  const [hints, setHints] = useState([])
  const [isCollapsed, setIsCollapsed] = useState(true)
  const navigate = useNavigate()
  // Assuming useAuth provides user ID if needed for API calls from hints
  // const { user } = useAuth();
  // Import the function to send messages to the gateway if hints trigger structured commands
  // This might come from a shared context or hook (e.g., useAdvisor)
  // const { sendMessageToGateway } = useAdvisor(); // Example

  const MAX_HINTS = 10 // Max hints to display

  useEffect(() => {
    if (lastJsonMessage && lastJsonMessage.type === "fusion_hint") {
      // Add basic validation for the payload
      const payload = lastJsonMessage.payload
      if (payload && typeof payload.text === "string") {
        const newHint = {
          id: uuidv4(),
          timestamp: Date.now(),
          type: payload.type || "info", // Default type
          text: payload.text,
          action: payload.action || null, // Optional action object
        }
        logger.info("Novo Hint recebido:", newHint)
        setHints((prevHints) => [newHint, ...prevHints].slice(0, MAX_HINTS))
      } else {
        logger.warn("Hint payload inválido recebido:", payload)
      }
    }
  }, [lastJsonMessage])

  // Handle Hint Action Clicks
  const handleHintAction = useCallback(
    (action, hintId) => {
      // Receive hintId
      logger.info("Ação do Hint clicada:", action)
      const { target, intent, parameters, label } = action || {}

      if (target && typeof target === "string") {
        // Internal Navigation Action
        logger.debug(`Navegando para: ${target}`)
        navigate(target)
      } else if (intent && typeof intent === "string") {
        // Structured Command Action for Advisor/Gateway
        logger.debug(`Enviando comando estruturado: Intent=${intent}, Params=${JSON.stringify(parameters)}`)

        // --- !! IMPLEMENTATION NEEDED !! ---
        // How to send this to AdvisorPage's sendMessageToGateway?
        // 1. Context/State Manager (Zustand, Redux, Jotai): Dispatch an action/update state.
        // 2. Prop Drilling (Complex): Pass sendMessageToGateway down from App -> Shell -> Panel.
        // 3. Shared Hook: Create a useAdvisor hook that provides sendMessageToGateway.
        // 4. Event Bus: Use a simple event emitter library.

        // Placeholder: Alert and navigate (remove this in real implementation)
        alert(
          `Simulando Comando Estruturado:nIntent: ${intent}nParams: ${JSON.stringify(parameters)}nn(Implementar envio ao Gateway via Contexto/Hook)`,
        )
        navigate("/advisor")

        /* Example using a hypothetical useAdvisor hook:  
          if (sendMessageToGateway && user) {  
              sendMessageToGateway(label || intent, {  
                  request_type: 'structured',  
                  payload: { intent, parameters },  
                  user_id: user.id // Pass user ID from context  
              });  
              // Maybe navigate to advisor? Or show feedback?  
              // navigate('/advisor');  
          } else {  
              logger.error("Cannot send structured hint action: sendMessageToGateway or user not available.");  
              // Show error message to user?  
          }  
          */
      } else {
        logger.warn("Ação do Hint inválida ou não reconhecida:", action)
      }

      // Optionally dismiss the hint after action click
      // handleDismissHint(hintId);

      // eslint-disable-next-line react-hooks/exhaustive-deps
    },
    [navigate /*, sendMessageToGateway, user */],
  ) // Add dependencies if using context/hooks

  // Handle Dismiss Clicks
  const handleDismissHint = useCallback((hintId) => {
    logger.debug(`Dispensando hint ID: ${hintId}`)
    setHints((prevHints) => prevHints.filter((h) => h.id !== hintId))
  }, [])

  return (
    <div
      className={`fixed top-0 right-0 h-full bg-fusion-dark border-l border-fusion-medium transition-all duration-300 z-20 ${
        isCollapsed ? "w-12" : "w-80"
      }`}
    >
      {/* Botão para colapsar/expandir */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -left-3 top-20 bg-fusion-medium text-fusion-light rounded-full p-1 z-10 shadow-md"
        aria-label={isCollapsed ? "Expandir painel" : "Colapsar painel"}
      >
        {isCollapsed ? <ChevronLeftIcon className="w-4 h-4" /> : <ChevronRightIcon className="w-4 h-4" />}
      </button>

      {/* Cabeçalho */}
      <div className="p-4 border-b border-fusion-medium flex items-center justify-between">
        {!isCollapsed && <h2 className="text-lg font-semibold text-fusion-text-primary">{title}</h2>}
      </div>

      {/* Conteúdo */}
      {!isCollapsed && (
        <div className="overflow-y-auto h-[calc(100%-60px)] p-4 scrollbar">
          {hints.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center text-center pt-16 text-fusion-light" /* Use pt instead of mt */
            >
              <LightBulbIcon className="w-10 h-10 mb-2 text-gray-600" />
              <p className="text-sm font-medium">Sem hints no momento.</p>
              <p className="text-xs">Sugestões contextuais aparecerão aqui.</p>
            </motion.div>
          )}
          <AnimatePresence>
            {hints.map((hint) => (
              <HintCard key={hint.id} hint={hint} onAction={handleHintAction} onDismiss={handleDismissHint} />
            ))}
          </AnimatePresence>
          {children}
        </div>
      )}
    </div>
  )
}

export default RightHintsPanel
