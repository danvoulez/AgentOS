import React, { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { WebSocketMessage, NewLogEventV2Message, LogEvent } from '../types/api';

interface WebSocketContextType {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: string | object) => void;
  logEvents: LogEvent[];
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

export const WebSocketProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { token, isAuthenticated } = useAuth();
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [logEvents, setLogEvents] = useState<LogEvent[]>([]);

  const connectWebSocket = useCallback(() => {
    if (!isAuthenticated || !token || socket) return;
    const wsUrl = `${import.meta.env.VITE_WS_BASE_URL}/updates?token=${token}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      setSocket(ws);
      ws.send("ping");
    };

    ws.onmessage = (event) => {
      try {
        const messageData = JSON.parse(event.data as string) as WebSocketMessage;
        setLastMessage(messageData);
        if (messageData.type === "new_log_event_v2") {
          const newLogEvent = (messageData as NewLogEventV2Message).payload;
          setLogEvents(prevEvents => [newLogEvent, ...prevEvents].slice(0, 50));
        }
      } catch (error) {
        if (event.data === "server_keepalive_ping") {
            // ignore
        }
      }
    };

    ws.onerror = () => {};
    ws.onclose = () => {
      setIsConnected(false);
      setSocket(null);
    };
    setSocket(ws);
    return () => {
      if (ws && ws.readyState === WebSocket.OPEN) ws.close();
      setSocket(null);
      setIsConnected(false);
    };
  }, [isAuthenticated, token, socket]);

  useEffect(() => {
    if (isAuthenticated && token && !socket) connectWebSocket();
    else if ((!isAuthenticated || !token) && socket && socket.readyState === WebSocket.OPEN) {
      socket.close();
      setSocket(null);
      setIsConnected(false);
    }
  }, [isAuthenticated, token, connectWebSocket, socket]);

  const sendMessage = (message: string | object) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      if (typeof message === 'object') socket.send(JSON.stringify(message));
      else socket.send(message);
    }
  };

  return (
    <WebSocketContext.Provider value={{ isConnected, lastMessage, sendMessage, logEvents }}>
      {children}
    </WebSocketContext.Provider>
  );
};