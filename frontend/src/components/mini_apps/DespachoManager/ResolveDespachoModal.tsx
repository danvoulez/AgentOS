import React, { useState, useEffect } from 'react';
import apiClient from '../../../apiClient';
import { CurrentStateDespacho, DESPACHO_STATUS_LITERAL, ActionResponseAPI, ResolveDespachoActionAPIPayload } from '../../../types/api';
import { motion } from 'framer-motion';

interface ResolveDespachoModalProps {
  despacho: CurrentStateDespacho | null;
  isOpen: boolean;
  onClose: () => void;
  onActionSuccess: (response: ActionResponseAPI) => void;
}

const ResolveDespachoModal: React.FC<ResolveDespachoModalProps> = ({ despacho, isOpen, onClose, onActionSuccess }) => {
  const [resolutionNotes, setResolutionNotes] = useState('');
  const resolvableStatuses: DESPACHO_STATUS_LITERAL[] = ["resolved_manual", "cancelled", "escalated", "in_progress"];
  const [selectedResolutionType, setSelectedResolutionType] = useState<DESPACHO_STATUS_LITERAL>("resolved_manual");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (despacho) {
      setResolutionNotes('');
      if (resolvableStatuses.includes(despacho.status as DESPACHO_STATUS_LITERAL)) {
        setSelectedResolutionType(despacho.status as DESPACHO_STATUS_LITERAL);
      } else {
        setSelectedResolutionType("resolved_manual");
      }
    }
  }, [despacho]);

  if (!isOpen || !despacho) return null;

  const handleSubmit = async () => {
    if (selectedResolutionType !== 'resolved_auto' && !resolutionNotes.trim() && selectedResolutionType !== 'in_progress') {
      setError("Notas de resolução são obrigatórias para este status.");
      return;
    }
    setIsSubmitting(true);
    setError('');
    try {
      const payload: ResolveDespachoActionAPIPayload = {
        despacho_id: despacho.id,
        resolution_type: selectedResolutionType,
        resolution_notes: resolutionNotes,
      };
      const response = await apiClient.post<ActionResponseAPI>('/actions/resolve_despacho', payload);
      onActionSuccess(response.data);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Falha ao submeter resolução do despacho.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const modalOverlayStyle: React.CSSProperties = { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 };
  const modalContentStyle: React.CSSProperties = { background: 'var(--theme-surface-color)', padding: 'var(--spacing-lg)', borderRadius: 'var(--border-radius-md)', boxShadow: 'var(--shadow-md)', minWidth: '450px', maxWidth: '90vw'};
  const inputStyle: React.CSSProperties = { width: '100%', padding: 'var(--spacing-sm)', boxSizing: 'border-box', marginBottom: 'var(--spacing-md)', border: '1px solid var(--theme-border-color)', borderRadius: 'var(--border-radius-sm)' };
  const buttonStyle: React.CSSProperties = { padding: 'var(--spacing-sm) var(--spacing-md)', cursor: 'pointer', border: 'none', borderRadius: 'var(--border-radius-sm)'};

  return (
    <motion.div style={modalOverlayStyle} initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}>
      <motion.div style={modalContentStyle} initial={{y:50, opacity:0}} animate={{y:0, opacity:1}} exit={{y:50, opacity:0}}>
        <h4 style={{marginTop:0, color: 'var(--theme-primary-color)'}}>Ação para Despacho: {despacho.despacho_type}</h4>
        <p><small>ID: {despacho.id}</small></p>
        <p><strong>Contexto:</strong> {despacho.summary_of_context || JSON.stringify(despacho.context_data)}</p>
        <div>
          <label htmlFor="resolutionType" style={{display: 'block', marginBottom: 'var(--spacing-xs)'}}>Novo Status:</label>
          <select id="resolutionType" value={selectedResolutionType} onChange={(e) => setSelectedResolutionType(e.target.value as DESPACHO_STATUS_LITERAL)} style={inputStyle}>
            {resolvableStatuses.map(s => <option key={s} value={s}>{s.replace("_", " ").toUpperCase()}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="resolutionNotes" style={{display: 'block', marginBottom: 'var(--spacing-xs)'}}>Notas da Ação{selectedResolutionType !== 'in_progress' ? '*' : ''}:</label>
          <textarea id="resolutionNotes" value={resolutionNotes} onChange={(e) => setResolutionNotes(e.target.value)} rows={4} style={inputStyle} placeholder="Detalhes da resolução, motivo do cancelamento/escalonamento, etc."/>
        </div>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <div style={{ marginTop: 'var(--spacing-md)', display: 'flex', justifyContent: 'flex-end', gap: 'var(--spacing-sm)' }}>
          <button type="button" onClick={onClose} disabled={isSubmitting} style={{...buttonStyle, background: 'var(--theme-background-color)', color: 'var(--theme-text-color)', border: '1px solid var(--theme-border-color)'}}>Cancelar</button>
          <button onClick={handleSubmit} disabled={isSubmitting} style={{...buttonStyle, background: 'var(--theme-primary-color)', color: 'white'}}>{isSubmitting ? "Processando..." : "Confirmar Ação"}</button>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default ResolveDespachoModal;