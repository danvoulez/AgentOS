import React, { useState, useEffect } from 'react';
import { Card, Text, Group, Avatar, Badge, ScrollArea, Loader, Button, Divider } from '@mantine/core';
import { IconUser, IconUsers, IconSend, IconRefresh } from '@tabler/icons-react';
import { getRecentConversations, getContactCRMDetails } from '../../api/whatsappService';

const ConversationItem = ({ conversation, onViewCRM }) => {
  const isGroup = conversation.isGroup;
  const lastMessage = conversation.lastMessage || {};
  
  // Formatar timestamp para exibição
  const formattedTime = lastMessage.timestamp 
    ? new Date(lastMessage.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '';

  return (
    <div style={{ padding: '10px 0', borderBottom: '1px solid #2C2E33' }}>
      <Group position="apart" spacing="sm">
        <Group>
          <Avatar radius="xl" color={isGroup ? 'blue' : 'violet'}>
            {isGroup ? <IconUsers size={24} /> : <IconUser size={24} />}
          </Avatar>
          
          <div>
            <Group spacing="xs">
              <Text size="sm" weight={500}>
                {conversation.name || conversation.phoneNumber}
              </Text>
              {isGroup && (
                <Badge size="xs" color="blue">Grupo</Badge>
              )}
              {conversation.hasUnread && (
                <Badge size="xs" color="red">Não Lido</Badge>
              )}
            </Group>
            
            <Text size="xs" color="dimmed" lineClamp={1}>
              {lastMessage.content || 'Nenhuma mensagem recente'}
            </Text>
          </div>
        </Group>
        
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
          {formattedTime && (
            <Text size="xs" color="dimmed">{formattedTime}</Text>
          )}
          
          {!isGroup && (
            <Button 
              variant="subtle" 
              size="xs" 
              compact 
              mt={5}
              onClick={() => onViewCRM(conversation.phoneNumber)}
            >
              Ver no CRM
            </Button>
          )}
        </div>
      </Group>
    </div>
  );
};

const ConversationList = ({ clientId }) => {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [crmData, setCrmData] = useState(null);
  const [crmLoading, setCrmLoading] = useState(false);

  const fetchConversations = async (reset = false) => {
    if (!clientId) return;
    
    setLoading(true);
    try {
      const newPage = reset ? 1 : page;
      const data = await getRecentConversations(clientId, { page: newPage, limit: 10 });
      
      if (reset) {
        setConversations(data.items);
      } else {
        setConversations(prev => [...prev, ...data.items]);
      }
      
      setHasMore(data.hasMore);
      setPage(reset ? 2 : newPage + 1);
      setError(null);
    } catch (err) {
      setError('Falha ao carregar conversas');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (clientId) {
      fetchConversations(true);
    } else {
      setConversations([]);
    }
  }, [clientId]);

  const handleViewCRM = async (phoneNumber) => {
    setCrmLoading(true);
    try {
      const data = await getContactCRMDetails(phoneNumber);
      setCrmData(data);
    } catch (err) {
      console.error('Erro ao buscar dados do CRM:', err);
    } finally {
      setCrmLoading(false);
    }
  };

  const handleLoadMore = () => {
    fetchConversations();
  };

  if (!clientId) {
    return (
      <Card p="xl" withBorder>
        <Text align="center" color="dimmed">
          Selecione um cliente para ver as conversas
        </Text>
      </Card>
    );
  }

  return (
    <Card p="md" withBorder style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Group position="apart" mb="md">
        <Text weight={500} size="lg">Conversas Recentes</Text>
        <Button 
          variant="subtle" 
          onClick={() => fetchConversations(true)} 
          leftIcon={<IconRefresh size={16} />}
        >
          Atualizar
        </Button>
      </Group>

      {error && (
        <Text color="red" mb="md">{error}</Text>
      )}

      <ScrollArea style={{ flex: 1 }}>
        {conversations.length === 0 && !loading ? (
          <Text color="dimmed" align="center" py="xl">
            Nenhuma conversa encontrada
          </Text>
        ) : (
          <div>
            {conversations.map(conversation => (
              <ConversationItem 
                key={conversation.id} 
                conversation={conversation} 
                onViewCRM={handleViewCRM}
              />
            ))}
            
            {hasMore && (
              <Button 
                fullWidth 
                variant="subtle" 
                onClick={handleLoadMore} 
                loading={loading}
                mt="md"
              >
                Carregar Mais
              </Button>
            )}
          </div>
        )}
        
        {loading && conversations.length === 0 && (
          <Group position="center" py="xl">
            <Loader />
            <Text>Carregando conversas...</Text>
          </Group>
        )}
      </ScrollArea>

      {crmData && (
        <Card withBorder p="md" mt="md">
          <Group position="apart" mb="xs">
            <Text weight={500}>Informações do CRM</Text>
            <Button 
              variant="subtle" 
              size="xs" 
              onClick={() => setCrmData(null)}
              compact
            >
              Fechar
            </Button>
          </Group>
          
          <Divider mb="md" />
          
          {crmLoading ? (
            <Loader size="sm" />
          ) : (
            <div>
              <Group>
                <Text size="sm" weight={500}>Nome:</Text>
                <Text size="sm">{crmData.name || 'N/A'}</Text>
              </Group>
              
              <Group mt="xs">
                <Text size="sm" weight={500}>Email:</Text>
                <Text size="sm">{crmData.email || 'N/A'}</Text>
              </Group>
              
              <Group mt="xs">
                <Text size="sm" weight={500}>Categoria:</Text>
                <Badge>{crmData.category || 'Não Categorizado'}</Badge>
              </Group>
              
              <Group mt="xs">
                <Text size="sm" weight={500}>Última Interação:</Text>
                <Text size="sm">
                  {crmData.lastInteraction 
                    ? new Date(crmData.lastInteraction).toLocaleString() 
                    : 'N/A'}
                </Text>
              </Group>
              
              <Button 
                mt="md" 
                leftIcon={<IconSend size={16} />}
                fullWidth
                variant="light"
                component="a"
                href={`/crm/contacts/${crmData.id}`}
                target="_blank"
              >
                Abrir Perfil Completo no CRM
              </Button>
            </div>
          )}
        </Card>
      )}
    </Card>
  );
};

export default ConversationList;
