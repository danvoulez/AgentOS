import React from 'react';
import { LogEvent } from '../../types/api';

interface LogActionPanelProps {
  logEvent: LogEvent;
  onAcionarClick: (logEvent: LogEvent) => void;
  onTriggerConsequence: (logEvent: LogEvent) => void;
}

const LogActionPanel: React.FC<LogActionPanelProps> = ({ logEvent, onAcionarClick, onTriggerConsequence }) => {
  const canAcionar = true; // lógica já existente
  const canTriggerConsequence =
    logEvent.consequence &&
    typeof logEvent.consequence === 'object' &&
    logEvent.consequence.status === 'awaiting_trigger' &&
    logEvent.consequence.type;

  return (
    <div style={{ marginTop: 'var(--spacing-sm)', paddingTop: 'var(--spacing-sm)', borderTop: '1px dashed var(--theme-border-color)', display: 'flex', gap: 'var(--spacing-sm)' }}>
      {canAcionar && (
        <button
          onClick={() => onAcionarClick(logEvent)}
          style={{padding: 'var(--spacing-xs) var(--spacing-sm)', fontSize: '0.9em', background: 'var(--theme-secondary-color)', color: 'white', border: 'none', borderRadius: 'var(--border-radius-sm)'}}
        >
          Acionar este Log...
        </button>
      )}
      {canTriggerConsequence && (
        <button
          onClick={() => onTriggerConsequence(logEvent)}
          style={{padding: 'var(--spacing-xs) var(--spacing-sm)', fontSize: '0.9em', background: 'var(--theme-primary-color)', color: 'white', border: 'none', borderRadius: 'var(--border-radius-sm)'}}
        >
          Acionar Consequência
        </button>
      )}
    </div>
  );
};

export default LogActionPanel;