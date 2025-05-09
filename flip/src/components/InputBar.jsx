"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { PaperAirplaneIcon, MicrophoneIcon } from "@heroicons/react/24/solid"
import { useAuth } from "../hooks/useAuth"
import apiClient from "../services/apiClient"

/**
 * InputBar component with text and voice input support
 * @param {string} draft - Current input value
 * @param {function} setDraft - Function to update input value
 * @param {function} setMessages - Function to update messages array
 * @param {function} setIsLoading - Function to update loading state
 * @param {string} conversationId - Optional conversation ID
 * @param {string} placeholder - Placeholder text for input
 */
function InputBar({
  draft,
  setDraft,
  setMessages,
  setIsLoading,
  conversationId,
  placeholder = "Digite sua mensagem ou clique no microfone para falar...",
}) {
  const { user } = useAuth()
  const textareaRef = useRef(null)
  const [isListening, setIsListening] = useState(false)
  const [speechSupported, setSpeechSupported] = useState(false)
  const recognitionRef = useRef(null)

  // Check if speech recognition is supported
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognition) {
      setSpeechSupported(true)
      recognitionRef.current = new SpeechRecognition()
      recognitionRef.current.continuous = true
      recognitionRef.current.interimResults = true
      recognitionRef.current.lang = "pt-BR"

      // Handle recognition results
      recognitionRef.current.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map((result) => result[0])
          .map((result) => result.transcript)
          .join("")

        setDraft(transcript)
      }

      // Handle recognition end
      recognitionRef.current.onend = () => {
        setIsListening(false)
      }

      // Handle recognition errors
      recognitionRef.current.onerror = (event) => {
        console.error("Speech recognition error:", event.error)
        setIsListening(false)
      }
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.onresult = null
        recognitionRef.current.onend = null
        recognitionRef.current.onerror = null
      }
    }
  }, [setDraft])

  // Auto-adjust textarea height
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = "auto"
      const scrollHeight = textarea.scrollHeight
      const maxHeight = 120 // ~5 lines
      textarea.style.height = `${Math.min(scrollHeight, maxHeight)}px`
      textarea.style.overflowY = scrollHeight > maxHeight ? "auto" : "hidden"
    }
  }, [draft])

  // Toggle speech recognition
  const toggleListening = useCallback(() => {
    if (!speechSupported) return

    if (isListening) {
      recognitionRef.current.stop()
      setIsListening(false)
    } else {
      setDraft("")
      recognitionRef.current.start()
      setIsListening(true)
    }
  }, [isListening, speechSupported, setDraft])

  // Handle input change
  const handleChange = (event) => {
    setDraft(event.target.value)
  }

  // Send message to backend
  const sendMessage = useCallback(async () => {
    if (!draft.trim()) return

    const userMessage = {
      id: Date.now().toString(),
      role: "user",
      content: draft.trim(),
      timestamp: new Date().toISOString(),
    }

    // Add user message to UI immediately
    setMessages((prev) => [...prev, userMessage])

    // Clear input and set loading state
    setDraft("")
    setIsLoading(true)

    try {
      // Prepare request payload
      const payload = {
        input: draft.trim(),
        metadata: {
          user_id: user?.id || "anonymous",
          mode: "advisor",
          conversation_id: conversationId || undefined,
        },
      }

      // Send request to backend
      const response = await apiClient.post("/process_request", payload)

      // Add AI response to messages
      if (response.data) {
        const aiMessage = {
          id: response.data.id || `ai-${Date.now()}`,
          role: "assistant",
          content: response.data.response || response.data.content || "",
          structured_data: response.data.structured_data,
          timestamp: new Date().toISOString(),
        }

        setMessages((prev) => [...prev, aiMessage])
      }
    } catch (error) {
      console.error("Error sending message:", error)

      // Add error message
      const errorMessage = {
        id: `error-${Date.now()}`,
        role: "system",
        content: "Ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.",
        timestamp: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }, [draft, setDraft, setMessages, setIsLoading, user, conversationId])

  // Handle key press (Enter to send, Shift+Enter for new line)
  const handleKeyDown = useCallback(
    (event) => {
      if (event.key === "Enter" && !event.shiftKey && draft.trim()) {
        event.preventDefault()
        sendMessage()
      }
    },
    [draft, sendMessage],
  )

  return (
    <div className="flex items-end p-3 md:p-4 bg-white border-t border-gray-200 space-x-3">
      <textarea
        ref={textareaRef}
        value={draft}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={isListening}
        rows="1"
        className="flex-1 resize-none bg-gray-50 rounded-lg p-3 text-sm text-gray-800 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 border border-gray-300 focus:border-blue-500 transition duration-150 ease-in-out disabled:opacity-60 disabled:cursor-not-allowed"
        style={{ minHeight: "44px", maxHeight: "120px" }}
      />

      {/* Voice input button */}
      {speechSupported && (
        <button
          onClick={toggleListening}
          type="button"
          className={`p-2 rounded-full transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white ${
            isListening
              ? "bg-red-500 hover:bg-red-600 text-white animate-pulse"
              : "bg-gray-200 hover:bg-gray-300 text-gray-700"
          }`}
          title={isListening ? "Parar de ouvir" : "Falar mensagem"}
        >
          <MicrophoneIcon className="w-5 h-5" />
        </button>
      )}

      {/* Send button */}
      <button
        onClick={sendMessage}
        disabled={!draft.trim() || isListening}
        className={`p-2 rounded-full transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white ${
          !draft.trim() || isListening
            ? "bg-gray-200 text-gray-400 cursor-not-allowed"
            : "bg-blue-600 hover:bg-blue-700 text-white"
        }`}
        title="Enviar Mensagem (Enter)"
      >
        <PaperAirplaneIcon className="w-5 h-5" />
      </button>
    </div>
  )
}

export default InputBar
