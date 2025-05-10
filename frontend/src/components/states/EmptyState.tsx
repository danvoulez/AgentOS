import React from 'react';
import { motion } from 'framer-motion';
import { DocumentMagnifyingGlassIcon } from '@heroicons/react/24/outline'; // Example icon
import './states.css';

interface EmptyStateProps {
  icon?: React.ElementType;
  title: string;
  message: string;
  actionText?: string;
  onActionClick?: () => void;
  className?: string;
}

const EmptyState: React.FC<EmptyStateProps> = ({
  icon: IconComponent = DocumentMagnifyingGlassIcon,
  title,
  message,
  actionText,
  onActionClick,
  className = '',
}) => {
  const motionVariants = {
    hidden: { opacity: 0, y: 20, scale: 0.98 },
    visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.4, ease: 'easeOut' } },
  };

  return (
    <motion.div
      className={`empty-state ${className}`}
      variants={motionVariants}
      initial="hidden"
      animate="visible"
      role="region"
      aria-live="polite"
    >
      <IconComponent className="empty-state-icon" aria-hidden="true" />
      <h3 className="empty-state-title">{title}</h3>
      <p className="empty-state-message">{message}</p>
      {actionText && onActionClick && (
        <div className="empty-state-action">
          <motion.button
            onClick={onActionClick}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            transition={{ duration: 0.15 }}
          >
            {actionText}
          </motion.button>
        </div>
      )}
    </motion.div>
  );
};

export default EmptyState;