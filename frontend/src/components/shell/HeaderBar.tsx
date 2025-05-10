import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useTheme, Theme } from '../../context/ThemeContext'; // Adjust path as needed
import { SunIcon, MoonIcon, ComputerDesktopIcon, PaintBrushIcon, ClockIcon, UserCircleIcon } from '@heroicons/react/24/outline';

const HeaderBar: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timerId = setInterval(() => setCurrentTime(new Date()), 1000 * 60); // Update every minute
    return () => clearInterval(timerId);
  }, []);

  const formattedTime = currentTime.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });
  
  // Mock user data
  const user = {
    name: 'Helena Vidal',
    avatarInitial: 'HV',
    // avatarUrl: 'path/to/avatar.jpg' // Optional image
  };


  const handleThemeChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setTheme(event.target.value as Theme);
  };

  const getThemeIcon = (currentTheme: Theme) => {
    switch (currentTheme) {
      case 'light': return <SunIcon />;
      case 'dark': return <MoonIcon />;
      case 'vibrant': return <PaintBrushIcon />; // Or other representative icon
      case 'muted': return <ComputerDesktopIcon />; // Or other
      default: return <PaintBrushIcon />;
    }
  };

  return (
    <motion.header
      className="header-bar"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
    >
      <div className="header-bar-left">
        {/* Placeholder for breadcrumbs or page title if needed */}
        <div className="header-bar-status-item">
            <ClockIcon />
            <span>{formattedTime}</span>
        </div>
      </div>
      <div className="header-bar-right">
        <div className="header-bar-status-item">
          {getThemeIcon(theme)}
          <select
            value={theme}
            onChange={handleThemeChange}
            className="header-bar-theme-select"
            aria-label="Select theme"
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="vibrant">Vibrant</option>
            <option value="muted">Muted</option>
          </select>
        </div>
        <div className="header-bar-user-profile" title={user.name}>
          <div className="header-bar-user-avatar">
            {/* {user.avatarUrl ? <img src={user.avatarUrl} alt={user.name} /> : user.avatarInitial} */}
            {user.avatarInitial} 
          </div>
          <span className="header-bar-user-name">{user.name.split(' ')[0]}</span> {/* Show first name */}
        </div>
      </div>
    </motion.header>
  );
};

export default HeaderBar;