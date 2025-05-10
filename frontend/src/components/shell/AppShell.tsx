import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'; // Example routing setup
import { AnimatePresence } from 'framer-motion';
import LeftMenu from './LeftMenu';
import HeaderBar from './HeaderBar';
import MainPanel from './MainPanel';
import { ThemeProvider } from '../../context/ThemeContext'; // Adjust path
import './appShell.css'; // Styles for the shell
import '../../styles/mosaic-tokens.css'; // Mosaic tokens (ensure this is loaded globally)

// Example placeholder pages
const DashboardPage: React.FC = () => <div style={{padding: '2rem'}}><h2>Dashboard Content</h2><p>This is the main dashboard area.</p></div>;
const FusionCorePage: React.FC = () => <div style={{padding: '2rem'}}><h2>Fusion AI Content</h2><p>Interact with Fusion AI modules here.</p></div>;
const ProfilePage: React.FC = () => <div style={{padding: '2rem'}}><h2>User Profile</h2><p>Manage your profile settings.</p></div>;
const SettingsPage: React.FC = () => <div style={{padding: '2rem'}}><h2>Application Settings</h2><p>Configure system-wide settings.</p></div>;


const AppShellContent: React.FC = () => {
  const [isMenuCollapsed, setIsMenuCollapsed] = useState(false);

  const toggleMenuCollapse = () => {
    setIsMenuCollapsed(!isMenuCollapsed);
  };

  return (
    <div className="app-shell">
      <LeftMenu isCollapsed={isMenuCollapsed} toggleCollapse={toggleMenuCollapse} />
      <div className="app-shell-main-container">
        <HeaderBar />
        <AnimatePresence mode="wait">
          <MainPanel />
        </AnimatePresence>
      </div>
    </div>
  );
}

// Main App component integrating the shell
const FusionApp: React.FC = () => {
  return (
    <ThemeProvider defaultTheme="dark"> {/* Or your preferred default */}
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppShellContent />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="fusion-core" element={<FusionCorePage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="settings" element={<SettingsPage />} />
            {/* Add other nested routes here */}
          </Route>
          {/* You can add other top-level routes like /login outside the shell */}
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
};

export default FusionApp; // Export the main app to render
// To use AppShell directly with children:
// export const AppShell = AppShellContent;