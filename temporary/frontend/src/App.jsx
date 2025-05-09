import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider } from "./context/AuthContext"
import { WebSocketProvider } from "./context/WebSocketContext"
import LoginPage from "./routes/LoginPage"
import AdvisorPage from "./routes/AdvisorPage"
import CommsPage from "./routes/CommsPage"
import ProtectedRoute from "./components/ProtectedRoute"

function App() {
  return (
    <Router>
      <AuthProvider>
        <WebSocketProvider>
          <div className="h-screen w-screen flex flex-col bg-fusion-deep text-fusion-text-primary">
            <Routes>
              <Route path="/login" element={<LoginPage />} />

              <Route
                path="/advisor"
                element={
                  <ProtectedRoute>
                    <AdvisorPage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/comms"
                element={
                  <ProtectedRoute>
                    <CommsPage />
                  </ProtectedRoute>
                }
              />

              {/* Redirecionar raiz para advisor */}
              <Route path="/" element={<Navigate to="/advisor" replace />} />

              {/* Rota 404 */}
              <Route
                path="*"
                element={
                  <div className="flex items-center justify-center h-screen">
                    <div className="text-center">
                      <h1 className="text-3xl font-bold mb-4">404 - Página não encontrada</h1>
                      <p className="mb-6">A página que você está procurando não existe.</p>
                      <a
                        href="/"
                        className="px-4 py-2 bg-fusion-purple text-white rounded-md hover:bg-fusion-purple-hover transition-colors"
                      >
                        Voltar para o início
                      </a>
                    </div>
                  </div>
                }
              />
            </Routes>
          </div>
        </WebSocketProvider>
      </AuthProvider>
    </Router>
  )
}

export default App
