import React, { useEffect, useState, useCallback } from 'react';
import apiClient from '../apiClient';
import { LogEvent, TimelineQueryResponse, ActionResponseAPI } from '../types/api';
import LogEventCard from '../components/LogEventCard';
import AcionamentoModal from '../components/acionamento/AcionamentoModal';
import { useWebSocket } from '../context/WebSocketContext';

const TimelinePage: React.FC = () => {
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedLogForAcionamento, setSelectedLogForAcionamento] = useState<LogEvent | null>(null);
  const [notification, setNotification] = useState<string | null>(null);
  const { logEvents: wsLogEvents } = useWebSocket();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(0);
  const limit = 10;

  const fetchTimeline = useCallback(async (page: number) => {
    setLoading(true);
    setError(null);
    try {
      const currentSkip = page * limit;
      const response = await apiClient.get<TimelineQueryResponse>(`/timeline?limit=${limit}&skip=${currentSkip}&sortOrder=desc`);
      setEvents(response.data.events);
      setTotalCount(response.data.total_count);
      setCurrentPage(page);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch timeline');
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetchTimeline(0);
  }, [fetchTimeline]);

  useEffect(() => {
    if (wsLogEvents.length > 0) {
        setEvents(prevDisplayedEvents => {
            const existingEventIds = new Set(prevDisplayedEvents.map(e => e.id));
            const newUniqueEventsFromWs = wsLogEvents.filter(wsEvent => !existingEventIds.has(wsEvent.id));
            if (newUniqueEventsFromWs.length > 0) {
                const combined = [...newUniqueEventsFromWs, ...prevDisplayedEvents];
                combined.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
                return combined.slice(0, Math.max(prevDisplayedEvents.length + newUniqueEventsFromWs.length, 50));
            }
            return prevDisplayedEvents;
        });
        const acionamentoEvent = wsLogEvents.find(e => e.type === 'log_acionado');
        if (acionamentoEvent && acionamentoEvent.data?.target_log_id) {
            // fetchTimeline(currentPage); // (opcional, depende do backend atualizar o log original no WS)
        }
    }
  }, [wsLogEvents, currentPage, fetchTimeline]);

  const handleOpenAcionamentoModal = (eventToAcionar: LogEvent) => {
    setSelectedLogForAcionamento(eventToAcionar);
    setIsModalOpen(true);
  };
  const handleCloseAcionamentoModal = () => {
    setIsModalOpen(false);
    setSelectedLogForAcionamento(null);
  };
  const handleAcionamentoSuccess = (response: ActionResponseAPI) => {
    setNotification(`Acionamento para Log ID ${response.data?.target_log_id || ''} registrado com sucesso! (Log de Acionamento ID: ${response.log_id})`);
    fetchTimeline(currentPage);
    setTimeout(() => setNotification(null), 5000);
  };

  const totalPages = Math.ceil(totalCount / limit);

  if (loading && currentPage === 0) return <p>Carregando timeline...</p>;
  if (error) return <p style={{ color: 'red' }}>Erro ao buscar timeline: {error}</p>;

  return (
    <div>
      <h2>LogLine Timeline Institucional</h2>
      {notification && <div style={{ padding: '10px', background: 'lightgreen', marginBottom: '10px' }}>{notification}</div>}
      <div style={{ margin: '1rem 0', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem' }}>
        <button onClick={() => fetchTimeline(Math.max(0, currentPage - 1))} disabled={currentPage === 0 || loading}>
          Anterior
        </button>
        <span>Página {currentPage + 1} de {totalPages} (Total: {totalCount} eventos)</span>
        <button onClick={() => fetchTimeline(Math.min(totalPages - 1, currentPage + 1))} disabled={currentPage >= totalPages - 1 || loading}>
          Próxima
        </button>
      </div>
      {events.length === 0 && !loading && <p>Nenhum evento na timeline encontrado.</p>}
      {events.map(event => (
        <LogEventCard key={event.id} event={event} onAcionarLog={handleOpenAcionamentoModal} />
      ))}
      {loading && currentPage > 0 && <p>Carregando mais eventos...</p>}
      {selectedLogForAcionamento && (
        <AcionamentoModal
          isOpen={isModalOpen}
          onClose={handleCloseAcionamentoModal}
          targetLogEvent={selectedLogForAcionamento}
          onAcionamentoSuccess={handleAcionamentoSuccess}
        />
      )}
    </div>
  );
};

export default TimelinePage;