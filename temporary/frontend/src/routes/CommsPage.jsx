"use client"

import { useState, useEffect } from "react"
import { useWebSocket } from "../hooks/useWebSocket"
import { useAuth } from "../hooks/useAuth"
import InputBar from "../components/InputBar"
import { useTypingEffect } from "../hooks/useTypingEffect"

const CommsPage = () => {
  const { user } = useAuth()
  const { isConnected, messages, sendMessage, error: wsError } = useWebSocket()
  const [draft, setDraft] = useState("")
  const [chatMessages, setChatMessages] = useState([])
  const [isTyping, setIsTyping] = useState(false)
  const { displayedText, isComplete } = useTypingEffect(
    isTyping ? "This is a demo of the typing effect. It simulates a real-time typing animation." : "",
    30,
  )

  // Process incoming WebSocket messages
  useEffect(() => {
    if (messages && messages.length > 0) {
      // Process only the latest message
      const latestMessage = messages[messages.length - 1]

      if (latestMessage.type === "chat") {
        setChatMessages((prev) => [...prev, latestMessage])
        setIsTyping(true)

        // Reset typing effect after message is complete
        setTimeout(() => {
          setIsTyping(false)
        }, 5000)
      }
    }
  }, [messages])

  const handleSend = () => {
    if (!draft.trim() || !isConnected) return

    const message = {
      type: "chat",
      content: draft,
      sender: user?.id,
      timestamp: new Date().toISOString(),
    }

    // Add user message to chat
    setChatMessages((prev) => [...prev, message])

    // Send via WebSocket
    sendMessage(message)

    // Clear draft
    setDraft("")
  }

  return (
    <div className="flex flex-col h-full bg-fusion-deep">
      <header className="p-4 border-b border-fusion-medium bg-fusion-dark">
        <h1 className="text-xl font-semibold text-fusion-text-primary">Communications</h1>
        <div className="flex items-center mt-1">
          <div className={`w-2 h-2 rounded-full mr-2 ${isConnected ? "bg-green-500" : "bg-red-500"}`}></div>
          <span className="text-sm text-fusion-light">{isConnected ? "Connected" : "Disconnected"}</span>
        </div>
      </header>

      <div className="flex-grow overflow-y-auto p-4 space-y-4">
        {chatMessages.length === 0 && (
          <p className="text-center text-fusion-light mt-10">No messages yet. Start a conversation!</p>
        )}

        {chatMessages.map((msg, index) => (
          <div
            key={index}
            className={`p-3 rounded-lg max-w-[80%] ${
              msg.sender === user?.id
                ? "bg-fusion-purple/20 ml-auto text-fusion-text-primary"
                : "bg-fusion-medium/40 text-fusion-text-primary"
            }`}
          >
            <p>{msg.content}</p>
            <span className="text-xs text-fusion-light block mt-1">{new Date(msg.timestamp).toLocaleTimeString()}</span>
          </div>
        ))}

        {isTyping && (
          <div className="p-3 rounded-lg max-w-[80%] bg-fusion-medium/40 text-fusion-text-primary">
            <p>{displayedText}</p>
            {!isComplete && <span className="inline-block w-1 h-4 bg-fusion-purple ml-1 animate-pulse"></span>}
          </div>
        )}

        {wsError && (
          <div className="p-3 rounded-md bg-fusion-error/20 border border-fusion-error/50 text-fusion-error text-sm text-center">
            {wsError}
          </div>
        )}
      </div>

      <div className="border-t border-fusion-medium">
        <InputBar
          draft={draft}
          setDraft={setDraft}
          sendAction={handleSend}
          placeholder="Type a message..."
          disabled={!isConnected}
        />
      </div>
    </div>
  )
}

export default CommsPage
