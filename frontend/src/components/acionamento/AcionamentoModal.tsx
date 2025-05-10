import React, { useState, useEffect } from 'react';
import { LogEvent, ACIONAMENTO_TYPE_LITERAL, AcionarLogEventActionAPIPayload } from '../../types/api';
import { useLogActions } from '../../hooks/useLogActions';

interface AcionamentoModalProps {
  isOpen: boolean;
  onClose: () => void;
  targetLogEvent: LogEvent;
  onAcionamentoSuccess: (response: any) => void;
}

const AcionamentoModal: React.FC<AcionamentoModalProps> = ({
  isOpen,
  onClose,
  targetLogEvent,
  onAcionamentoSuccess,
}) => {
  const [acionamentoType, setAcionamentoType] = useState<ACIONAMENTO_TYPE_LITERAL>('confirmar_fato');
  const [motivo, setMotivo] = useState('');
  const [dadosAdicionaisJson, setDadosAdicionaisJson] = useState('');
  const [testemunhaAcionadaId, setTestemunhaAcionadaId] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const { acionarLog, isAcionando, errorAcionamento } = useLogActions();

  useEffect(() => {
    if (isOpen) {
      setAcionamentoType('confirmar_fato');
      setMotivo('');
      setDadosAdicionaisJson('');
      setTestemunhaAcionadaId('');
      setFormError(null);
    }
  }, [isOpen, targetLogEvent]);

  const isMotivoRequired = (type: ACIONAMENTO_TYPE_LITERAL): boolean => {
    return ["negar_fato", "propor_ajuste", "denunciar_ma_fe", "acionar_testemunha"].includes(type);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (isMotivoRequired(acionamentoType) && !motivo.trim()) {
      setFormError("O campo 'Motivo' é obrigatório para este tipo de acionamento.");
      return;
    }
    if (acionamentoType === "acionar_testemunha" && !testemunhaAcionadaId.trim()) {
      setFormError("O campo 'ID da Testemunha a Acionar' é obrigatório.");
      return;
    }

    let parsedDadosAdicionais: Record<string, any> | undefined = undefined;
    if (dadosAdicionaisJson.trim()) {
      try {
        parsedDadosAdicionais = JSON.parse(dadosAdicionaisJson);
        if (typeof parsedDadosAdicionais !== 'object' || parsedDadosAdicionais === null) {
          throw new Error("Deve ser um objeto JSON válido.");
        }
      } catch (err) {
        setFormError("Formato inválido para 'Dados Adicionais'. Deve ser um JSON válido.");
        return;
      }
    }

    const payload: AcionarLogEventActionAPIPayload = {
      target_log_id: targetLogEvent.id,
      acionamento_type: acionamentoType,
      motivo: motivo.trim() || null,
      dados_adicionais: parsedDadosAdicionais || null,
      testemunha_acionada_id: acionamentoType === "acionar_testemunha" ? testemunhaAcionadaId.trim() : null,
    };

    try {
      const response = await acionarLog(payload);
      onAcionamentoSuccess(response);
      onClose();
    } catch (err: any) {
      setFormError(err.message || "Falha ao submeter acionamento.");
    }
  };

  if (!isOpen) return null;

  const modalStyle: React.CSSProperties = { position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', background: 'var(--theme-surface-color)', padding: 'var(--spacing-lg)', borderRadius: 'var(--border-radius-md)', boxShadow: 'var(--shadow-md)', zIndex: 1000, minWidth: '400px', maxWidth: '600px' };
  const inputStyle: React.CSSProperties = { width: 'calc(100% - 16px)', padding: 'var(--spacing-sm)', marginBottom: 'var(--spacing-sm)', border: '1px solid var(--theme-border-color)', borderRadius: 'var(--border-radius-sm)' };
  const labelStyle: React.CSSProperties = { display: 'block', marginBottom: 'var(--spacing-xs)', fontWeight: 'bold' };
  const buttonStyle: React.CSSProperties = { padding: 'var(--spacing-sm) var(--spacing-md)', cursor: 'pointer', border: 'none', borderRadius: 'var(--border-radius-sm)'};

  return (
    <div style={modalStyle}>
      <h3 style={{marginTop: 0, color: 'var(--theme-primary-color)'}}>Acionar LogEvent: {targetLogEvent.id.substring(0,12)}... ({targetLogEvent.type})</h3>
      <p>Timestamp Original: {new Date(targetLogEvent.timestamp).toLocaleString()}</p>
      <p>Autor Original: {targetLogEvent.author}</p>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="acionamentoType" style={labelStyle}>Tipo de Acionamento:</label>
          <select id="acionamentoType" value={acionamentoType} onChange={(e) => setAcionamentoType(e.target.value as ACIONAMENTO_TYPE_LITERAL)} required style={inputStyle}>
            <option value="confirmar_fato">Confirmar Fato</option>
            <option value="negar_fato">Contestar/Negar Fato</option>
            <option value="acionar_testemunha">Acionar Testemunha</option>
            <option value="propor_ajuste">Sugerir Ajuste/Correção</option>
            <option value="denunciar_ma_fe">Denunciar Má Fé</option>
            <option value="solicitar_consequencia">Solicitar Consequência</option>
          </select>
        </div>
        {isMotivoRequired(acionamentoType) && (
          <div>
            <label htmlFor="motivo" style={labelStyle}>Motivo{isMotivoRequired(acionamentoType) ? '*' : ''}:</label>
            <textarea id="motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={3} required={isMotivoRequired(acionamentoType)} style={inputStyle} />
          </div>
        )}
        {acionamentoType === "acionar_testemunha" && (
          <div>
            <label htmlFor="testemunhaAcionadaId" style={labelStyle}>ID da Testemunha a Acionar*:</label>
            <input type="text" id="testemunhaAcionadaId" value={testemunhaAcionadaId} onChange={(e) => setTestemunhaAcionadaId(e.target.value)} required style={inputStyle} />
          </div>
        )}
        {acionamentoType === "propor_ajuste" && (
            <p style={{fontSize: '0.9em', color: 'var(--theme-text-muted-color)'}}>
                Para 'Propor Ajuste', detalhe a correção sugerida em 'Dados Adicionais' (formato JSON). Ex: {`{"campo_a_corrigir": "novo_valor"}`}
            </p>
        )}
        <div>
          <label htmlFor="dadosAdicionaisJson" style={labelStyle}>Dados Adicionais (JSON, Opcional):</label>
          <textarea id="dadosAdicionaisJson" value={dadosAdicionaisJson} onChange={(e) => setDadosAdicionaisJson(e.target.value)} rows={4} placeholder='Ex: {"evidencia_url": "..."}' style={inputStyle} />
        </div>
        {(formError || errorAcionamento) && <p style={{ color: 'red' }}>{formError || errorAcionamento}</p>}
        <div style={{ marginTop: 'var(--spacing-md)', display: 'flex', justifyContent: 'flex-end', gap: 'var(--spacing-sm)' }}>
          <button type="button" onClick={onClose} disabled={isAcionando} style={{...buttonStyle, background: 'var(--theme-background-color)', color: 'var(--theme-text-color)', border: '1px solid var(--theme-border-color)'}}>Cancelar</button>
          <button type="submit" disabled={isAcionando} style={{...buttonStyle, background: 'var(--theme-primary-color)', color: 'white'}}>{isAcionando ? 'Processando...' : 'Submeter Acionamento'}</button>
        </div>
      </form>
    </div>
  );
};

export default AcionamentoModal;