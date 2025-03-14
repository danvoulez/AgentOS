import React, { useState } from 'react';
import { Grid, Button, Group, Title, Container } from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';

import ClientList from '../components/WhatsApp/ClientList';
import ClientStats from '../components/WhatsApp/ClientStats';
import ConversationList from '../components/WhatsApp/ConversationList';
import AddClientForm from '../components/WhatsApp/AddClientForm';

const WhatsAppDashboard = () => {
  const [selectedClientId, setSelectedClientId] = useState(null);
  const [addClientModalOpen, setAddClientModalOpen] = useState(false);
  
  const handleClientSelect = (clientId) => {
    setSelectedClientId(clientId);
  };
  
  const handleClientAdded = () => {
    // Pode ser implementado para selecionar automaticamente o novo cliente
  };
  
  return (
    <Container fluid>
      <Group position="apart" mb={30}>
        <Title order={2}>Dashboard WhatsApp</Title>
        <Button 
          leftIcon={<IconPlus size={16} />} 
          onClick={() => setAddClientModalOpen(true)}
        >
          Novo Cliente
        </Button>
      </Group>
      
      <Grid>
        <Grid.Col span={12} md={4}>
          <ClientList onSelectClient={handleClientSelect} />
        </Grid.Col>
        
        <Grid.Col span={12} md={8}>
          <Grid>
            <Grid.Col span={12}>
              <ClientStats clientId={selectedClientId} />
            </Grid.Col>
            
            <Grid.Col span={12} style={{ marginTop: 16 }}>
              <ConversationList clientId={selectedClientId} />
            </Grid.Col>
          </Grid>
        </Grid.Col>
      </Grid>
      
      <AddClientForm 
        opened={addClientModalOpen}
        onClose={() => setAddClientModalOpen(false)}
        onClientAdded={handleClientAdded}
      />
    </Container>
  );
};

export default WhatsAppDashboard;
