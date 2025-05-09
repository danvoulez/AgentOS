"use client"
import { useLocation, useNavigate } from "react-router-dom"
import { motion, AnimatePresence } from "framer-motion"
import LeftMenu from "./LeftMenu"
import RightHintsPanel from "./RightHintsPanel"
import { useWebSocket } from "../context/WebSocketContext"
// Adjust icons as needed
import { ChatBubbleLeftEllipsisIcon, LightBulbIcon, WifiIcon, WifiSlashIcon } from "@heroicons/react/24/outline"

// Flip View Button Component
function FlipViewButton() {
  const location = useLocation()
  const navigate = useNavigate()
  const isAdvisor = location.pathname.includes("/advisor")
  const toggleView = () => navigate(isAdvisor ? "/comms" : "/advisor")

  return (
    <motion.button
      onClick={toggleView}
      title={isAdvisor ? "Ir para Comms (Chat)" : "Ir para Advisor (IA)"}
      // Use theme colors
      className="p-2 rounded-full bg-fusion-purple hover:bg-fusion-purple-hover text-white transition-colors duration-200 ease-out z-10 shadow-lg focus:outline-none focus:ring-2 focus:ring-fusion-purple-light focus:ring-offset-2 focus:ring-offset-fusion-deep"
      whileHover={{ scale: 1.1, rotate: isAdvisor ? -10 : 10 }}
      whileTap={{ scale: 0.9 }}
    >
      {isAdvisor ? <ChatBubbleLeftEllipsisIcon className="w-5 h-5" /> : <LightBulbIcon className="w-5 h-5" />}
    </motion.button>
  )
}

// WebSocket Status Indicator Component
function WebSocketStatusIndicator() {
  const { isConnected, error: wsError } = useWebSocket()

  return (
    <div
      className={`flex items-center px-2.5 py-1 rounded-full text-xs font-medium border transition-colors duration-300 ${
        isConnected
          ? "bg-green-600/20 border-green-500/50 text-green-300" // Use success colors
          : "bg-red-600/20 border-red-500/50 text-red-300 animate-pulse-light" // Use error colors + pulse
      }`}
      title={
        isConnected ? "WebSocket Conectado" : wsError ? `WebSocket Desconectado: ${wsError}` : "WebSocket Desconectado"
      }
    >
      {isConnected ? <WifiIcon className="w-3.5 h-3.5 mr-1.5" /> : <WifiSlashIcon className="w-3.5 h-3.5 mr-1.5" />}
      {isConnected ? "Online" : "Offline"}
      {wsError && !isConnected && <span className="ml-1">⚠️</span>}
    </div>
  )
}

// Main Shell Component
function FusionShell({ children }) {
  const location = useLocation()

  // Page transition animation variants
  const pageVariants = {
    initial: { opacity: 0, scale: 0.99, filter: "blur(3px)" },
    in: { opacity: 1, scale: 1, filter: "blur(0px)", transition: { duration: 0.35, ease: [0.43, 0.13, 0.23, 0.96] } }, // Use custom ease
    out: { opacity: 0, scale: 0.99, filter: "blur(3px)", transition: { duration: 0.2, ease: "easeIn" } },
  }

  // Constants for layout widths (consider moving to config or theme)
  const leftMenuWidthClass = "w-64" // TODO: Add responsive classes lg:w-64 md:w-20 sm:w-16 etc.
  const rightPanelWidthClass = "w-72" // TODO: Add responsive classes lg:w-72 md:w-64 sm:hidden etc.

  return (
    // Use theme colors
    <div className="flex h-screen bg-fusion-deep text-fusion-text-primary relative overflow-hidden">
      {/* Left Menu (Fixed Position) */}
      {/* Ensure z-index is high */}
      <div className={`${leftMenuWidthClass} fixed top-0 left-0 h-full z-40 flex-shrink-0`}>
        {" "}
        {/* Added flex-shrink-0 */}
        <LeftMenu />
      </div>

      {/* Main Content Area (Handles the right side, including header and panel) */}
      {/* Use padding/margins to account for fixed menus */}
      {/* Use dynamic margin based on left menu width class */}
      <div className={`flex-1 flex flex-col ml-64`}>
        {" "}
        {/* ADJUST ml-64 IF leftMenuWidthClass CHANGES */}
        {/* Header Bar (Fixed above main scrollable content) */}
        {/* Use theme colors, backdrop blur, z-index */}
        {/* Use dynamic left margin based on left menu width class */}
        <div
          className={`fixed top-0 left-64 right-0 h-14 px-4 flex items-center justify-end space-x-4 z-20 bg-fusion-deep/80 backdrop-blur-sm border-b border-fusion-medium/30`}
        >
          {" "}
          {/* ADJUST left-64 IF leftMenuWidthClass CHANGES */}
          {/* WebSocket Status Indicator */}
          <WebSocketStatusIndicator />
          {/* Flip View Button */}
          <FlipViewButton />
        </div>
        {/* Scrollable Content + Right Panel Container */}
        <div className="flex flex-1 pt-14 overflow-hidden">
          {" "}
          {/* pt-14 for header height */}
          {/* Main Scrollable Content */}
          {/* Apply custom scrollbar style */}
          {/* Use dynamic right margin based on right panel width class */}
          <main className="flex-1 overflow-y-auto scrollbar mr-72">
            {" "}
            {/* ADJUST mr-72 IF rightPanelWidthClass CHANGES */}
            {/* AnimatePresence for route transitions */}
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname} // Key triggers animation on route change
                initial="initial"
                animate="in"
                exit="out"
                variants={pageVariants}
                className="h-full w-full p-4 md:p-6" // Add padding inside the animated div
              >
                {children}
              </motion.div>
            </AnimatePresence>
          </main>
          {/* Right Hints Panel (Fixed position relative to the outer container) */}
          {/* Ensure z-index is high but below modals if any */}
          <div className={`${rightPanelWidthClass} fixed top-0 right-0 h-full z-30 flex-shrink-0`}>
            {" "}
            {/* Fixed positioning */}
            <RightHintsPanel />
          </div>
        </div>
      </div>
    </div>
  )
}

export default FusionShell
