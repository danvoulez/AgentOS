import React from 'react';
import { useAuth } from '../hooks/useAuth';
import { useWebSocket } from '../context/WebSocketContext';

const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const { isConnected, lastMessage } = useWebSocket();

  return (
    <div>
      <h2>Dashboard</h2>
      <p>Welcome, {user?.profile?.first_name || user?.username}!</p>
      <p>Your ID: {user?.id}</p>
      <p>Your Roles: {user?.roles.join(', ')}</p>
      <h3>WebSocket Status:</h3>
      <p>Connected: {isConnected ? 'Yes' : 'No'}</p>
      {lastMessage && (
        <div>
          <h4>Last WebSocket Message:</h4>
          <pre style={{ background: '#f0f0f0', padding: '10px', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
            {JSON.stringify(lastMessage, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default DashboardPage;