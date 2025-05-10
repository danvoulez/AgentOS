import React, { useState, useEffect } from 'react';
import apiClient from '../../apiClient';
import { useAuth } from '../../hooks/useAuth';
import {
  LogEvent,
  LogEventEditorPayload,
  LogEventValidationResponse,
  ActionResponseAPI,
} from '../../types/api';

const JsonDisplay: React.FC<{ data: any }> = ({ data }) => (
  <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', background: '#f0f0f0', padding: '0.5rem', borderRadius: '4px', fontSize: '0.8rem' }}>
    {JSON.stringify(data, null, 2)}
  </pre>
);

const JsonEditor: React.FC<{ value: string; onChange: (value: string) => void; label: string; error?: string }> = ({ value, onChange, label, error }) => (
  <div style={{ marginBottom: '1rem' }}>
    <label style={{ display: 'block', marginBottom: '0.3rem' }}>{label}:</label>
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      rows={8}
      style={{ width: '100%', padding: '0.5rem', border: `1px solid ${error ? 'red' : '#ccc'}`, borderRadius: '4px' }}
    />
    {error && <p style={{ color: 'red', fontSize: '0.8rem' }}>{error}</p>}
  </div>
);

const LogEventEditorPage: React.FC = () => {
  const { user, token } = useAuth();
  const [tab, setTab] = useState<'create' | 'inspect'>('create');
  const [logEventJson, setLogEventJson] = useState<string>('');
  const [logEventPayload, setLogEventPayload] = useState<LogEventEditorPayload | null>(null);
  const [validationResult, setValidationResult] = useState<LogEventValidationResponse | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const [inspectLogId, setInspectLogId] = useState('');
  const [inspectedLogEvent, setInspectedLogEvent] = useState<LogEvent | null>(null);
  const [isInspecting, setIsInspecting] = useState(false);

  useEffect(() => {
    if (user && tab === 'create' && (!logEventPayload || !logEventPayload.author || logEventPayload.author === '')) {
      const defaultAuthor = `user:${user.id}`;
      const defaultWitness = `admin:ui:${user.username || user.email}`;
      setLogEventPayload({
        ...logEventPayload,
        author: defaultAuthor,
        witness: defaultWitness,
        channel: "admin_ui",
        origin: "LogEventEditor"
      } as LogEventEditorPayload);
    }
  }, [user, tab, logEventPayload]);

  useEffect(() => {
    if (tab === 'create') {
      try {
        const parsed = JSON.parse(logEventJson);
        setLogEventPayload(parsed as LogEventEditorPayload);
        setMessage(null);
      } catch (e: any) {
        setMessage({ type: 'error', text: 'Invalid JSON: ' + e.message });
        setLogEventPayload(null);
      }
    }
  }, [logEventJson, tab]);

  const handleValidate = async () => {
    if (!logEventPayload) {
      setMessage({ type: 'error', text: 'Invalid LogEvent JSON payload. Please fix errors.' });
      return;
    }
    setIsProcessing(true);
    setMessage(null);
    try {
      const response = await apiClient.post<LogEventValidationResponse>(
        '/admin/validate_log_event_proposal',
        logEventPayload
      );
      setValidationResult(response.data);
      setMessage({ type: response.data.is_valid ? 'success' : 'error', text: response.data.message });
    } catch (err: any) {
      setValidationResult(null);
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Validation failed due to server error.' });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleForceLog = async () => {
    if (!logEventPayload) {
      setMessage({ type: 'error', text: 'Invalid LogEvent JSON payload. Please fix errors.' });
      return;
    }
    if (!validationResult?.is_valid) {
        setMessage({ type: 'error', text: 'Please validate the LogEvent first and ensure it is valid.' });
        return;
    }
    setIsProcessing(true);
    setMessage(null);
    try {
      const response = await apiClient.post<ActionResponseAPI>(
        '/admin/force_log_event',
        logEventPayload
      );
      setMessage({ type: 'success', text: response.data.message + ` Log ID: ${response.data.log_id}` });
      setLogEventJson('');
      setLogEventPayload(null);
      setValidationResult(null);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to force log due to server error.' });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleInspect = async () => {
    if (!inspectLogId.trim()) {
      setMessage({ type: 'error', text: 'Please enter a LogEvent ID to inspect.' });
      return;
    }
    setIsInspecting(true);
    setInspectedLogEvent(null);
    setMessage(null);
    try {
      const response = await apiClient.get<LogEvent>(`/timeline/${inspectLogId}`);
      setInspectedLogEvent(response.data);
      setMessage({ type: 'success', text: `LogEvent ${inspectLogId} fetched successfully.` });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to fetch LogEvent.' });
      setInspectedLogEvent(null);
    } finally {
      setIsInspecting(false);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: 'auto', padding: '2rem', background: 'var(--theme-surface-color)', borderRadius: '8px', boxShadow: 'var(--shadow-md)' }}>
      <h2>LogEvent Admin Editor</h2>
      <div style={{ marginBottom: '1rem', borderBottom: '1px solid var(--theme-border-color)', paddingBottom: '1rem' }}>
        <button onClick={() => setTab('create')} style={{ marginRight: '1rem', padding: '0.5rem 1rem', background: tab === 'create' ? 'var(--theme-primary-color)' : 'var(--theme-background-color)', color: tab === 'create' ? 'white' : 'var(--theme-text-color)' }}>
          Create/Validate LogEvent
        </button>
        <button onClick={() => setTab('inspect')} style={{ padding: '0.5rem 1rem', background: tab === 'inspect' ? 'var(--theme-primary-color)' : 'var(--theme-background-color)', color: tab === 'inspect' ? 'white' : 'var(--theme-text-color)' }}>
          Inspect Existing LogEvent
        </button>
      </div>
      {message && <p style={{ color: message.type === 'error' ? 'red' : 'green', fontWeight: 'bold' }}>{message.text}</p>}
      {tab === 'create' && (
        <div>
          <JsonEditor 
            label="LogEvent JSON Payload"
            value={logEventJson}
            onChange={setLogEventJson}
            error={message?.type === 'error' && message.text.startsWith('Invalid JSON') ? message.text : undefined}
          />
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
            <button onClick={handleValidate} disabled={isProcessing || !logEventPayload} style={{ padding: '0.75rem 1.5rem', background: 'var(--theme-secondary-color)', color: 'white', border: 'none', borderRadius: '4px' }}>
              {isProcessing ? 'Validando...' : 'Validate Proposal'}
            </button>
            <button onClick={handleForceLog} disabled={isProcessing || !logEventPayload || !validationResult?.is_valid} style={{ padding: '0.75rem 1.5rem', background: 'var(--theme-primary-color)', color: 'white', border: 'none', borderRadius: '4px' }}>
              {isProcessing ? 'Forçando...' : 'Force LogEvent (Admin)'}
            </button>
          </div>
          {validationResult && (
            <div style={{ border: `1px solid ${validationResult.is_valid ? 'green' : 'red'}`, padding: '1rem', borderRadius: '4px', background: validationResult.is_valid ? '#e6ffe6' : '#ffe6e6' }}>
              <h4>Validation Result: {validationResult.is_valid ? 'VALID' : 'INVALID'}</h4>
              <p>{validationResult.message}</p>
              {validationResult.validation_errors && validationResult.validation_errors.length > 0 && (
                <div>
                  <h5>Errors:</h5>
                  <ul>
                    {validationResult.validation_errors.map((err, index) => <li key={index} style={{ color: 'red' }}>{err}</li>)}
                  </ul>
                </div>
              )}
              {validationResult.validated_log_event && (
                <div>
                  <h5>Validated LogEvent Payload:</h5>
                  <JsonDisplay data={validationResult.validated_log_event} />
                </div>
              )}
            </div>
          )}
        </div>
      )}
      {tab === 'inspect' && (
        <div>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
            <input
              type="text"
              value={inspectLogId}
              onChange={(e) => setInspectLogId(e.target.value)}
              placeholder="Enter LogEvent ID (e.g., evt_uuid_string)"
              style={{ flexGrow: 1, padding: '0.75rem' }}
            />
            <button onClick={handleInspect} disabled={isInspecting || !inspectLogId.trim()} style={{ padding: '0.75rem 1.5rem' }}>
              {isInspecting ? 'Buscando...' : 'Inspect'}
            </button>
          </div>
          {inspectedLogEvent && (
            <div style={{ border: `1px solid green`, padding: '1rem', borderRadius: '4px', background: '#e6ffe6' }}>
              <h4>Inspected LogEvent:</h4>
              <JsonDisplay data={inspectedLogEvent} />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default LogEventEditorPage;