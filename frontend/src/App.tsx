import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { WebSocketProvider } from './context/WebSocketContext';
import Navbar from './components/Layout/Navbar';
import ProtectedRoute from './components/Layout/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import TimelinePage from './pages/TimelinePage';
import InventoryPage from './pages/InventoryPage';

const App: React.FC = () => (
  <AuthProvider>
    <WebSocketProvider>
      <Router>
        <Navbar />
        <div style={{ padding: '1rem' }}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/timeline" element={<TimelinePage />} />
              <Route path="/inventory" element={<InventoryPage />} />
            </Route>
            <Route 
              path="*" 
              element={
                localStorage.getItem('authToken') ? <Navigate to="/" /> : <Navigate to="/login" />
              } 
            />
          </Routes>
        </div>
      </Router>
    </WebSocketProvider>
  </AuthProvider>
);

export default App;