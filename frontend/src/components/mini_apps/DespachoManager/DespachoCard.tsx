import React from 'react';
import { CurrentStateDespacho } from '../../../types/api';
import { motion } from 'framer-motion';

interface DespachoCardProps {
  despacho: CurrentStateDespacho;
  onSelectToResolve: (despacho: CurrentStateDespacho) => void;
}

const DespachoCard: React.FC<DespachoCardProps> = ({ despacho, onSelectToResolve }) => {
  const isOverdue =
    despacho.due_at &&
    new Date(despacho.due_at) < new Date() &&
    !['resolved_auto', 'resolved_manual', 'cancelled'].includes(despacho.status);
  const cardStyle: React.CSSProperties = {
    background: 'var(--theme-surface-color)',
    border: `var(--border-width) solid ${isOverdue ? 'var(--theme-accent-color)' : 'var(--theme-border-color)'}`,
    padding: 'var(--spacing-md)',
    marginBottom: 'var(--spacing-md)',
    borderRadius: 'var(--border-radius-md)',
    boxShadow: 'var(--shadow-sm)',
  };
  const titleStyle = {
    marginTop: 0,
    color: isOverdue ? 'var(--theme-accent-color)' : 'var(--theme-primary-color)',
  };

  return (
    <motion.div style={cardStyle} layout initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <h5 style={titleStyle}>
        {despacho.despacho_type} {isOverdue && '(ATRASADO)'}
      </h5>
      <p style={{ fontSize: '0.8em', color: 'var(--theme-text-muted-color)' }}>ID: {despacho.id}</p>
      <p>
        <strong>Status:</strong>{' '}
        <span
          style={{
            fontWeight: 'bold',
            color:
              despacho.status === 'pending'
                ? 'orange'
                : despacho.status.startsWith('resolved')
                ? 'green'
                : 'var(--theme-text-color)',
          }}
        >
          {despacho.status}
        </span>
      </p>
      <p>
        <strong>Atribuído a:</strong> {despacho.assigned_to_name || despacho.assigned_to || 'Não atribuído'}
      </p>
      <p>
        <strong>Criado em:</strong> {new Date(despacho.created_at).toLocaleString()}
      </p>
      {despacho.due_at && (
        <p>
          <strong>Prazo:</strong> {new Date(despacho.due_at).toLocaleString()}
        </p>
      )}
      {despacho.summary_of_context && (
        <p>
          <strong>Contexto:</strong> {despacho.summary_of_context}
        </p>
      )}
      {despacho.notes && despacho.notes.length > 0 && (
        <details>
          <summary style={{ cursor: 'pointer', fontSize: '0.9em' }}>
            Ver Notas ({despacho.notes.length})
          </summary>
          <ul style={{ fontSize: '0.85em', maxHeight: '100px', overflowY: 'auto' }}>
            {despacho.notes.map((note, i) => (
              <li key={i}>
                <em>{new Date(note.timestamp).toLocaleTimeString()}:</em> {note.note}
              </li>
            ))}
          </ul>
        </details>
      )}
      {!despacho.status.startsWith('resolved') && despacho.status !== 'cancelled' && (
        <motion.button
          onClick={() => onSelectToResolve(despacho)}
          style={{
            marginTop: 'var(--spacing-sm)',
            padding: 'var(--spacing-xs) var(--spacing-sm)',
            background: 'var(--theme-secondary-color)',
            color: 'white',
            border: 'none',
            borderRadius: 'var(--border-radius-sm)',
          }}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
        >
          Resolver/Atualizar Status
        </motion.button>
      )}
    </motion.div>
  );
};

export default DespachoCard;