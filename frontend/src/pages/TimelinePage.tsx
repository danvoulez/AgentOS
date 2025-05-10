import React, { useEffect, useState } from 'react';
import apiClient from '../apiClient';
import { LogEvent, TimelineQueryResponse } from '../types/api';
import LogEventCard from '../components/LogEventCard';
import { useWebSocket } from '../context/WebSocketContext';

const TimelinePage: React.FC = () => {
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [skip, setSkip] = useState(0);
  const limit = 20;
  const { logEvents: wsLogEvents } = useWebSocket();

  const fetchTimeline = async (currentSkip: number) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get<TimelineQueryResponse>(`/timeline?limit=${limit}&skip=${currentSkip}`);
      setEvents(currentSkip === 0 ? response.data.events : prev => [...prev, ...response.data.events]);
      setTotalCount(response.data.total_count);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch timeline');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTimeline(0); }, []);
  useEffect(() => {
    if (wsLogEvents.length > 0) {
      setEvents(prevDisplayedEvents => {
        const newEventsFromWs = wsLogEvents.filter(
            wsEvent => !prevDisplayedEvents.find(dispEvent => dispEvent.id === wsEvent.id)
        );
        const combined = [...newEventsFromWs, ...prevDisplayedEvents];
        combined.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
        return combined.slice(0, 50);
      });
    }
  }, [wsLogEvents]);

  const handleLoadMore = () => {
    const newSkip = skip + limit;
    if (newSkip < totalCount) {
      setSkip(newSkip);
      fetchTimeline(newSkip);
    }
  };

  if (loading && skip === 0) return <p>Loading timeline...</p>;
  if (error) return <p style={{ color: 'red' }}>Error fetching timeline: {error}</p>;

  return (
    <div>
      <h2>LogLine Timeline</h2>
      {events.map(event => (
        <LogEventCard key={event.id} event={event} />
      ))}
      {events.length < totalCount && !loading && (
        <button onClick={handleLoadMore} style={{ marginTop: '1rem', padding: '0.5rem 1rem' }}>
          Load More ({events.length}/{totalCount})
        </button>
      )}
      {loading && skip > 0 && <p>Loading more events...</p>}
    </div>
  );
};

export default TimelinePage;