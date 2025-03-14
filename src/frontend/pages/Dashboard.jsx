import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Grid, 
  Card, 
  Text, 
  Title, 
  Group, 
  Badge, 
  SimpleGrid,
  RingProgress,
  useMantineTheme
} from '@mantine/core';
import { IconUsers, IconDeviceWatch, IconMessage, IconAlertCircle } from '@tabler/icons-react';
import { api } from '../utils/api';

// Stats card component
const StatsCard = ({ title, value, icon, color }) => {
  const theme = useMantineTheme();
  
  return (
    <Card withBorder p="md" radius="md">
      <Group position="apart">
        <Text size="xs" color="dimmed" weight={700} transform="uppercase">
          {title}
        </Text>
        <ThemeIcon color={color} variant="light" size={38} radius="md">
          {icon}
        </ThemeIcon>
      </Group>
      <Text size="xl" weight={700} mt="md">
        {value}
      </Text>
    </Card>
  );
};

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalUsers: 0,
    activeDevices: 0,
    pendingMessages: 0,
    alerts: 0
  });
  
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setIsLoading(true);
        // In a real app, this would be a call to your API
        // const data = await api.get('/dashboard/stats');
        
        // Simulated data for now
        setTimeout(() => {
          setStats({
            totalUsers: 124,
            activeDevices: 42,
            pendingMessages: 18,
            alerts: 3
          });
          setIsLoading(false);
        }, 800);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  return (
    <Container size="lg" py="xl">
      <Title order={2} mb="xl">System Dashboard</Title>
      
      {isLoading ? (
        <Text>Loading dashboard data...</Text>
      ) : (
        <>
          <SimpleGrid cols={4} breakpoints={[
            { maxWidth: 'md', cols: 2 },
            { maxWidth: 'xs', cols: 1 }
          ]}>
            <StatsCard 
              title="Total Users" 
              value={stats.totalUsers} 
              icon={<IconUsers size={20} />} 
              color="blue" 
            />
            <StatsCard 
              title="Active Devices" 
              value={stats.activeDevices} 
              icon={<IconDeviceWatch size={20} />} 
              color="green" 
            />
            <StatsCard 
              title="Pending Messages" 
              value={stats.pendingMessages} 
              icon={<IconMessage size={20} />} 
              color="violet" 
            />
            <StatsCard 
              title="Alerts" 
              value={stats.alerts} 
              icon={<IconAlertCircle size={20} />} 
              color="red" 
            />
          </SimpleGrid>
          
          <Grid mt="xl">
            <Grid.Col md={8}>
              <Card withBorder p="md" radius="md">
                <Title order={3} size="h4" mb="md">System Activity</Title>
                <Text color="dimmed">
                  Activity chart would go here in a real implementation
                </Text>
              </Card>
            </Grid.Col>
            
            <Grid.Col md={4}>
              <Card withBorder p="md" radius="md" h="100%">
                <Title order={3} size="h4" mb="md">Service Status</Title>
                <Group position="center" mt="md">
                  <RingProgress
                    size={140}
                    thickness={14}
                    sections={[
                      { value: 40, color: 'green' },
                      { value: 15, color: 'orange' },
                      { value: 15, color: 'red' }
                    ]}
                    label={
                      <Text size="xs" align="center" weight={700}>
                        80% Online
                      </Text>
                    }
                  />
                </Group>
                <Group position="apart" mt="md">
                  <Text size="sm">Messaging</Text>
                  <Badge color="green">Online</Badge>
                </Group>
                <Group position="apart" mt="xs">
                  <Text size="sm">People Service</Text>
                  <Badge color="green">Online</Badge>
                </Group>
                <Group position="apart" mt="xs">
                  <Text size="sm">Media Service</Text>
                  <Badge color="orange">Degraded</Badge>
                </Group>
                <Group position="apart" mt="xs">
                  <Text size="sm">Order Service</Text>
                  <Badge color="red">Offline</Badge>
                </Group>
              </Card>
            </Grid.Col>
          </Grid>
        </>
      )}
    </Container>
  );
};

export default Dashboard;
