import React from 'react';

interface TooltipHeaderProps {
  title?: string;
  tooltipText?: string;
}

const TooltipHeader: React.FC<TooltipHeaderProps> = ({ title, tooltipText }) => {
  if (!title && !tooltipText) return null;
  return (
    <div style={{ display: 'flex', alignItems: 'center', marginBottom: 'var(--spacing-sm)' }}>
      {title && <h4 style={{ margin: 0, marginRight: 'var(--spacing-xs)', color: 'var(--theme-text-color)' }}>{title}</h4>}
      {tooltipText && (
        <div title={tooltipText} style={{ cursor: 'help' }}>
          <span style={{ color: 'var(--theme-text-muted-color)', fontSize: 'var(--font-size-sm)' }}>(i)</span>
        </div>
      )}
    </div>
  );
};

export default TooltipHeader;