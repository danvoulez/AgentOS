"use client"

import { useState } from "react"
import { useNavigate, useLocation } from "react-router-dom"
import { useAuth } from "../hooks/useAuth"
import LoadingSpinner from "../components/LoadingSpinner"

const LoginPage = () => {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [errorMessage, setErrorMessage] = useState("")
  const { login, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // Get the redirect path from location state or default to "/"
  const from = location.state?.from?.pathname || "/"

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrorMessage("")

    if (!email || !password) {
      setErrorMessage("Email and password are required")
      return
    }

    try {
      await login(email, password)
      // Redirect to the page they tried to visit or home
      navigate(from, { replace: true })
    } catch (error) {
      setErrorMessage(error.message || "Login failed. Please try again.")
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-fusion-deep p-4">
      <div className="w-full max-w-md bg-fusion-dark rounded-lg shadow-lg p-6 space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-fusion-text-primary">Login to Advisor</h1>
          <p className="text-fusion-light mt-2">Enter your credentials to access your account</p>
        </div>

        {errorMessage && (
          <div className="bg-fusion-error/20 border border-fusion-error/50 text-fusion-error p-3 rounded-md text-sm">
            {errorMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-fusion-text-primary mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 bg-fusion-medium/40 border border-fusion-medium rounded-md focus:outline-none focus:ring-2 focus:ring-fusion-purple text-fusion-text-primary"
              placeholder="your.email@example.com"
              disabled={loading}
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-fusion-text-primary mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 bg-fusion-medium/40 border border-fusion-medium rounded-md focus:outline-none focus:ring-2 focus:ring-fusion-purple text-fusion-text-primary"
              placeholder="••••••••"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-fusion-purple hover:bg-fusion-purple-hover text-white font-medium py-2 px-4 rounded-md transition duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-fusion-purple disabled:opacity-60 disabled:cursor-not-allowed flex justify-center items-center"
          >
            {loading ? (
              <>
                <LoadingSpinner size="w-5 h-5" color="border-white" /> <span className="ml-2">Logging in...</span>
              </>
            ) : (
              "Login"
            )}
          </button>
        </form>
      </div>
    </div>
  )
}

export default LoginPage
