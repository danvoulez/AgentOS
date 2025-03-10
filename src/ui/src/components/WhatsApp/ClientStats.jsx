import React, { useState, useEffect } from 'react';
import { Card, Text, Group, SimpleGrid, RingProgress, Skeleton, Badge } from '@mantine/core';
import { getClientStats } from '../../api/whatsappService';

const StatCard = ({ title, value, loading }) => (
  <Card p="lg" withBorder shadow="sm">
    <Text size="sm" color="dimmed">{title}</Text>
    {loading ? (
      <Skeleton height={30} width="70%" mt={6} />
    ) : (
      <Text size="xl" weight={700}>{value}</Text>
    )}
  </Card>
);

const ClientStats = ({ clientId }) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      if (!clientId) return;
      
      setLoading(true);
      try {
        const data = await getClientStats(clientId);
        setStats(data);
        setError(null);
      } catch (err) {
        setError('Falha ao carregar estatísticas');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    // Atualizar a cada 2 minutos
    const interval = setInterval(fetchStats, 120000);
    return () => clearInterval(interval);
  }, [clientId]);

  if (!clientId) {
    return (
      <Card p="xl" withBorder>
        <Text align="center" color="dimmed">
          Selecione um cliente para ver as estatísticas
        </Text>
      </Card>
    );
  }

  if (error) {
    return (
      <Card p="xl" withBorder>
        <Text color="red">{error}</Text>
      </Card>
    );
  }

  return (
    <Card p="md" withBorder>
      <Group position="apart" mb="md">
        <Text weight={500} size="lg">Estatísticas do Cliente</Text>
        <Badge size="lg">{clientId}</Badge>
      </Group>

      <SimpleGrid cols={3} breakpoints={[{ maxWidth: 'sm', cols: 1 }]}>
        <StatCard 
          title="Mensagens Recebidas Hoje" 
          value={loading ? '' : stats?.messagesReceived?.today} 
          loading={loading} 
        />
        <StatCard 
          title="Mensagens Enviadas Hoje" 
          value={loading ? '' : stats?.messagesSent?.today} 
          loading={loading} 
        />
        <StatCard 
          title="Contatos Ativos" 
          value={loading ? '' : stats?.activeContacts} 
          loading={loading} 
        />
      </SimpleGrid>

      <SimpleGrid cols={2} mt="md" breakpoints={[{ maxWidth: 'sm', cols: 1 }]}>
        <Card p="lg" withBorder shadow="sm">
          <Text size="sm" color="dimmed" mb="md">Taxa de Resposta</Text>
          {loading ? (
            <Skeleton height={150} />
          ) : (
            <Group position="center">
              <RingProgress
                size={150}
                thickness={16}
                sections={[{ value: stats?.responseRate || 0, color: 'blue' }]}
                label={
                  <Text size="lg" align="center" weight={700}>
                    {stats?.responseRate}%
                  </Text>
                }
              />
            </Group>
          )}
        </Card>
        
        <Card p="lg" withBorder shadow="sm">
          <Text size="sm" color="dimmed" mb="md">Tráfego de Mensagens (7 dias)</Text>
          {loading ? (
            <Skeleton height={150} />
          ) : (
            <Group position="center">
              <SimpleGrid cols={2} spacing="xs">
                <StatCard 
                  title="Recebidas" 
                  value={stats?.messagesReceived?.week || 0} 
                  loading={false} 
                />
                <StatCard 
                  title="Enviadas" 
                  value={stats?.messagesSent?.week || 0} 
                  loading={false} 
                />
              </SimpleGrid>
            </Group>
          )}
        </Card>
      </SimpleGrid>
    </Card>
  );
};

export default ClientStats;
