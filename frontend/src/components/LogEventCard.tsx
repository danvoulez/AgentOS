import React from 'react';
import { LogEvent } from '../types/api';

interface LogEventCardProps {
  event: LogEvent;
}

const LogEventCard: React.FC<LogEventCardProps> = ({ event }) => (
  <div style={{ border: '1px solid #ccc', margin: '0.5rem', padding: '0.5rem', borderRadius: '4px' }}>
    <p><strong>ID:</strong> {event.id}</p>
    <p><strong>Timestamp:</strong> {new Date(event.timestamp).toLocaleString()}</p>
    <p><strong>Type:</strong> {event.type}</p>
    <p><strong>Author:</strong> {event.author}</p>
    <p><strong>Witness:</strong> {event.witness}</p>
    {event.channel && <p><strong>Channel:</strong> {event.channel}</p>}
    {event.origin && <p><strong>Origin:</strong> {event.origin}</p>}
    <details>
      <summary>Data (Click to expand)</summary>
      <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', background: '#f9f9f9', padding: '0.5rem' }}>
        {JSON.stringify(event.data, null, 2)}
      </pre>
    </details>
    {event.consequence && (
      <details>
        <summary>Consequence (Click to expand)</summary>
        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', background: '#f0f0f0', padding: '0.5rem' }}>
          {JSON.stringify(event.consequence, null, 2)}
        </pre>
      </details>
    )}
    {event.meta && (
      <details>
        <summary>Meta (Click to expand)</summary>
        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', background: '#e9e9e9', padding: '0.5rem' }}>
          {JSON.stringify(event.meta, null, 2)}
        </pre>
      </details>
    )}
  </div>
);

export default LogEventCard;