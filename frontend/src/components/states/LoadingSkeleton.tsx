import React from 'react';
import { motion } from 'framer-motion';
import './states.css'; // Shared CSS for state components

type SkeletonVariant = 'line' | 'block' | 'circle' | 'listItem';

interface LoadingSkeletonProps {
  variant?: SkeletonVariant;
  count?: number; // For repeating lines or list items
  width?: string | number;
  height?: string | number;
  className?: string;
  style?: React.CSSProperties;
  // Props specific to listItem
  showAvatar?: boolean;
  linesPerItem?: number;
}

const SkeletonLine: React.FC<Pick<LoadingSkeletonProps, 'width' | 'className'>> = ({ width, className }) => (
  <div
    className={`skeleton-line ${className || ''}`}
    style={{ width: width || '100%' }}
  />
);

const SkeletonBlock: React.FC<Pick<LoadingSkeletonProps, 'width' | 'height' | 'className'>> = ({ width, height, className }) => (
  <div
    className={`skeleton-block ${className || ''}`}
    style={{ width: width || '100%', height: height || '100px' }}
  />
);

const SkeletonCircle: React.FC<Pick<LoadingSkeletonProps, 'width' | 'height' | 'className'>> = ({ width, height, className }) => (
  <div
    className={`skeleton-circle ${className || ''}`}
    style={{ width: width || '40px', height: height || '40px' }}
  />
);

const SkeletonListItem: React.FC<Pick<LoadingSkeletonProps, 'showAvatar' | 'linesPerItem'>> = ({ showAvatar = true, linesPerItem = 2}) => (
  <div className="skeleton-list-item">
    {showAvatar && <SkeletonCircle className="skeleton-list-item-avatar" />}
    <div className="skeleton-list-item-text">
      {Array.from({ length: linesPerItem }).map((_, i) => (
        <SkeletonLine key={i} className={i === 0 ? 'medium' : 'short'} />
      ))}
    </div>
  </div>
);


const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  variant = 'line',
  count = 1,
  width,
  height,
  className = '',
  style,
  showAvatar,
  linesPerItem,
}) => {
  const motionVariants = {
    hidden: { opacity: 0.5 }, // Start slightly visible for less harsh pop-in
    visible: { opacity: 1, transition: { duration: 0.3 } },
  };

  const renderSkeletons = () => {
    const items = [];
    for (let i = 0; i < count; i++) {
      switch (variant) {
        case 'block':
          items.push(<SkeletonBlock key={i} width={width} height={height} className={className} />);
          break;
        case 'circle':
          items.push(<SkeletonCircle key={i} width={width} height={height} className={className} />);
          break;
        case 'listItem':
          items.push(<SkeletonListItem key={i} showAvatar={showAvatar} linesPerItem={linesPerItem} />);
          break;
        case 'line':
        default:
          items.push(<SkeletonLine key={i} width={width} className={className} />);
          break;
      }
    }
    return items;
  };

  return (
    <motion.div
      className="loading-skeleton"
      variants={motionVariants}
      initial="hidden"
      animate="visible"
      style={style}
      aria-live="polite"
      aria-busy="true"
    >
      {renderSkeletons()}
    </motion.div>
  );
};

export default LoadingSkeleton;