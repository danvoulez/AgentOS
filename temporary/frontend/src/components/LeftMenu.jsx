"use client"
import { NavLink, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext" // Assuming useAuth hook exists
import { motion } from "framer-motion" // For subtle animations
// Import icons
import {
  ChatBubbleLeftRightIcon,
  SparklesIcon,
  ArrowLeftOnRectangleIcon,
  UserCircleIcon,
  BuildingOffice2Icon,
  Cog6ToothIcon,
  CircleStackIcon,
  ScaleIcon, // Added more icons
  RectangleStackIcon, // Example for Orders
  TruckIcon, // Example for Delivery
  ClipboardDocumentCheckIcon, // Example for Agreements
  CheckCircleIcon as CheckCircleIconOutline, // Example for Tasks
} from "@heroicons/react/24/outline"

function LeftMenu() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    try {
      await logout() // Assume logout might be async
      navigate("/login")
    } catch (error) {
      console.error("Logout failed:", error)
      // Show error to user?
    }
  }

  // NavLink styling function
  const getLinkClasses = ({ isActive }) => {
    const baseClasses =
      "flex items-center space-x-3 px-3 py-2.5 rounded-md text-sm font-medium transition-all duration-150 ease-in-out group"
    // Use theme colors
    const activeClasses = "bg-fusion-purple text-white shadow-inner"
    const inactiveClasses = "text-fusion-text-secondary hover:bg-fusion-medium hover:text-fusion-text-primary"
    return `${baseClasses} ${isActive ? activeClasses : inactiveClasses}`
  }

  // Placeholder links data structure (for scalability)
  const mainNav = [
    { to: "/comms", icon: ChatBubbleLeftRightIcon, label: "Comms" },
    { to: "/advisor", icon: SparklesIcon, label: "Advisor IA" },
  ]
  const operationsNav = [
    { to: "/orders", icon: RectangleStackIcon, label: "Sales", disabled: true },
    { to: "/delivery", icon: TruckIcon, label: "Delivery", disabled: true },
    { to: "/tasks", icon: CheckCircleIconOutline, label: "Tasks", disabled: true },
    { to: "/agreements", icon: ClipboardDocumentCheckIcon, label: "Agreements", disabled: true },
    // Add Stock?
  ]
  const adminNav = [
    { to: "/office", icon: BuildingOffice2Icon, label: "Office", disabled: true },
    { to: "/settings", icon: Cog6ToothIcon, label: "Settings", disabled: true },
    { to: "/audit", icon: CircleStackIcon, label: "Audit", disabled: true },
    { to: "/finance", icon: ScaleIcon, label: "Finance", disabled: true },
  ]

  const renderNavLink = (item) => {
    if (item.disabled) {
      return (
        <span key={item.label} className={`${getLinkClasses({ isActive: false })} opacity-50 cursor-not-allowed`}>
          <item.icon className="w-5 h-5 text-fusion-light" />
          <span>{item.label} (Em breve)</span>
        </span>
      )
    }
    return (
      <NavLink key={item.to} to={item.to} className={getLinkClasses}>
        {({ isActive }) => (
          <>
            <item.icon
              className={`w-5 h-5 ${isActive ? "text-white" : "text-fusion-light group-hover:text-fusion-purple-light"}`}
            />
            <span>{item.label}</span>
          </>
        )}
      </NavLink>
    )
  }

  return (
    // Use theme colors, manage height/scroll internally if needed
    <div className="w-full h-full bg-fusion-dark text-fusion-text-primary flex flex-col border-r border-fusion-medium/50 shadow-lg">
      {/* Logo/Header */}
      <div className="h-14 flex items-center justify-center flex-shrink-0 border-b border-fusion-medium/50">
        {" "}
        {/* Reduced height to match header */}
        {/* Replace with your actual logo */}
        {/* <img src="/path/to/logo.svg" alt="Fusion Logo" className="h-8 w-auto"/> */}
        <h1 className="text-2xl font-bold text-fusion-purple tracking-tight">Fusion</h1>
      </div>

      {/* Navigation Area (Scrollable) */}
      {/* Apply custom scrollbar style */}
      <nav className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar">
        {/* Main Navigation */}
        <div className="space-y-1">{mainNav.map(renderNavLink)}</div>

        {/* Operations Section */}
        <div>
          <span className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Operações</span>
          <ul className="mt-2 space-y-1">
            {operationsNav.map((item) => (
              <li key={item.label}>{renderNavLink(item)}</li>
            ))}
          </ul>
        </div>

        {/* Admin Section */}
        <div>
          <span className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Admin</span>
          <ul className="mt-2 space-y-1">
            {adminNav.map((item) => (
              <li key={item.label}>{renderNavLink(item)}</li>
            ))}
          </ul>
        </div>
      </nav>

      {/* Footer with User Info & Logout */}
      <div className="flex-shrink-0 border-t border-fusion-medium/50 p-4">
        {
          user ? (
            <div className="flex items-center space-x-3 mb-4">
              {/* Placeholder for user avatar - replace UserCircleIcon if you have avatars */}
              <UserCircleIcon className="w-9 h-9 text-fusion-light" />
              <div className="overflow-hidden flex-1">
                <p className="text-sm font-medium text-fusion-text-primary truncate" title={user.email}>
                  {user.profile?.first_name || user.username || "Usuário"}
                </p>
                <p className="text-xs text-fusion-text-secondary truncate">{user.email}</p>
              </div>
            </div>
          ) : (
            <div className="h-14 mb-4"></div>
          ) /* Placeholder for height */
        }

        <motion.button
          onClick={handleLogout}
          // Use theme colors for button styling (red-700/80 -> fusion-error/80)
          className="w-full flex items-center justify-center space-x-2 px-3 py-2 rounded-md text-sm font-medium bg-fusion-medium hover:bg-fusion-error/80 text-fusion-text-secondary hover:text-white transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-fusion-error focus:ring-offset-2 focus:ring-offset-fusion-dark"
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
        >
          <ArrowLeftOnRectangleIcon className="w-5 h-5" />
          <span>Logout</span>
        </motion.button>
      </div>
    </div>
  )
}

export default LeftMenu
