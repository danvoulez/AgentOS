import React from 'react';
import { motion } from 'framer-motion';
import { Outlet, useLocation } from 'react-router-dom'; // For page transitions

interface MainPanelProps {
  children?: React.ReactNode; // Allow direct children or Outlet
}

const MainPanel: React.FC<MainPanelProps> = ({ children }) => {
  const location = useLocation(); // For keying motion component for transitions

  const pageVariants = {
    initial: { opacity: 0, y: 20, filter: 'blur(4px)' },
    in: { opacity: 1, y: 0, filter: 'blur(0px)' },
    out: { opacity: 0, y: -20, filter: 'blur(4px)' },
  };

  const pageTransition = {
    type: 'tween',
    ease: 'anticipate', // Or 'circOut', 'easeInOut'
    duration: 0.4,
  };

  return (
    <main className="main-panel">
      <motion.section
        key={location.pathname} // Animate on route change
        className="main-panel-content"
        initial="initial"
        animate="in"
        exit="out"
        variants={pageVariants}
        transition={pageTransition}
      >
        {children || <Outlet />} 
      </motion.section>
    </main>
  );
};

export default MainPanel;