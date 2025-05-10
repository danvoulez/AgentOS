import React from 'react';
import { NavLink } from 'react-router-dom'; // Assuming use of React Router
import { motion } from 'framer-motion';
import {
  HomeIcon,
  Squares2X2Icon, // For Dashboard/Modules
  Cog6ToothIcon, // For Settings
  UserCircleIcon, // For Profile
  ArrowLeftOnRectangleIcon, // For Logout
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
  SparklesIcon // Fusion/App specific
} from '@heroicons/react/24/outline'; // Using outline icons

interface NavItem {
  to: string;
  text: string;
  icon: React.ElementType;
}

interface LeftMenuProps {
  isCollapsed: boolean;
  toggleCollapse: () => void;
}

const navItems: NavItem[] = [
  { to: '/dashboard', text: 'Dashboard', icon: Squares2X2Icon },
  { to: '/fusion-core', text: 'Fusion AI', icon: SparklesIcon },
  { to: '/profile', text: 'Profile', icon: UserCircleIcon },
  { to: '/settings', text: 'Settings', icon: Cog6ToothIcon },
];

const LeftMenu: React.FC<LeftMenuProps> = ({ isCollapsed, toggleCollapse }) => {
  const handleLogout = () => {
    // Implement actual logout logic here
    console.log('Logout clicked');
  };

  return (
    <motion.aside
      className={`left-menu ${isCollapsed ? 'collapsed' : ''}`}
      animate={{ width: isCollapsed ? 'var(--left-menu-width-collapsed)' : 'var(--left-menu-width-expanded)' }}
      transition={{ duration: 0.25, ease: 'easeInOut' }}
    >
      <div className="left-menu-header">
        <div className="left-menu-logo">
            <SparklesIcon /> {/* Replace with actual logo SVG if available */}
            {!isCollapsed && <span>Fusion</span>}
        </div>
      </div>

      <nav>
        <ul>
          {navItems.map((item) => (
            <motion.li
              key={item.to}
              className="left-menu-item"
              whileHover={{ scale: isCollapsed ? 1.1 : 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <NavLink
                to={item.to}
                className={({ isActive }) => (isActive ? 'active' : '')}
                title={item.text}
              >
                <item.icon className="left-menu-icon" />
                <span className="left-menu-item-text">{item.text}</span>
              </NavLink>
            </motion.li>
          ))}
        </ul>
      </nav>

      <div className="left-menu-footer">
        <motion.button
          className="left-menu-button"
          onClick={handleLogout}
          title="Logout"
          whileHover={{ scale: isCollapsed ? 1.1 : 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <ArrowLeftOnRectangleIcon className="left-menu-icon" />
          <span className="left-menu-item-text">Logout</span>
        </motion.button>
        <motion.button
          className="left-menu-button"
          style={{ marginTop: '0.5rem' }}
          onClick={toggleCollapse}
          title={isCollapsed ? 'Expand Menu' : 'Collapse Menu'}
          whileHover={{ scale: isCollapsed ? 1.1 : 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          {isCollapsed ? (
            <ChevronDoubleRightIcon className="left-menu-icon" />
          ) : (
            <ChevronDoubleLeftIcon className="left-menu-icon" />
          )}
          <span className="left-menu-item-text">{isCollapsed ? 'Expand' : 'Collapse'}</span>
        </motion.button>
      </div>
    </motion.aside>
  );
};

export default LeftMenu;