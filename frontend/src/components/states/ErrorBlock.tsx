import React from 'react';
import { motion } from 'framer-motion';
import { ExclamationTriangleIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import './states.css';

interface ErrorBlockProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  retryText?: string;
  className?: string;
  inline?: boolean; // For a more compact, inline display
}

const ErrorBlock: React.FC<ErrorBlockProps> = ({
  title = "An Error Occurred",
  message,
  onRetry,
  retryText = "Try Again",
  className = '',
  inline = false,
}) => {
  const motionVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' } },
  };

  return (
    <motion.div
      className={`error-block ${inline ? 'inline' : ''} ${className}`}
      variants={motionVariants}
      initial="hidden"
      animate="visible"
      role="alert"
    >
      <ExclamationTriangleIcon className="error-block-icon" aria-hidden="true" />
      <div className="error-block-content">
        <h4 className="error-block-title">{title}</h4>
        <p className="error-block-message">{message}</p>
      </div>
      {onRetry && (
        <div className="error-block-action">
          <motion.button
            onClick={onRetry}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            transition={{ duration: 0.15 }}
          >
            <ArrowPathIcon style={{width: '1em', height: '1em', marginRight: '0.5em', verticalAlign: 'middle'}}/>
            {retryText}
          </motion.button>
        </div>
      )}
    </motion.div>
  );
};

export default ErrorBlock;