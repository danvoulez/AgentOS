import React, { useState } from 'react';
import { 
  Modal, 
  TextInput, 
  Button, 
  Group, 
  Select, 
  Stack,
  Text,
  Alert
} from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import { addWhatsAppClient } from '../../api/whatsappService';

const AddClientForm = ({ opened, onClose, onClientAdded }) => {
  const [formData, setFormData] = useState({
    phoneNumber: '',
    type: 'webjs',
    name: ''
  });
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const handleChange = (field) => (value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validação básica
    if (!formData.phoneNumber || !formData.type) {
      setError('Por favor, preencha todos os campos obrigatórios');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await addWhatsAppClient(formData);
      onClientAdded(result);
      onClose();
    } catch (err) {
      setError('Falha ao adicionar o cliente WhatsApp');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Modal 
      opened={opened} 
      onClose={onClose}
      title="Adicionar Novo Cliente WhatsApp"
      size="md"
    >
      <form onSubmit={handleSubmit}>
        <Stack spacing="md">
          {error && (
            <Alert icon={<IconAlertCircle size={16} />} color="red" title="Erro">
              {error}
            </Alert>
          )}
          
          <TextInput
            label="Nome do Cliente"
            placeholder="Ex: Marketing, Suporte, etc."
            value={formData.name}
            onChange={(e) => handleChange('name')(e.currentTarget.value)}
            required
          />
          
          <TextInput
            label="Número de Telefone"
            placeholder="Ex: 5511999999999"
            description="Código do país + DDD + número, sem símbolos ou espaços"
            value={formData.phoneNumber}
            onChange={(e) => handleChange('phoneNumber')(e.currentTarget.value)}
            required
          />
          
          <Select
            label="Tipo de Cliente"
            placeholder="Selecione o tipo"
            description={
              <Text size="xs" color="dimmed">
                Direto (Web.js) para mensagens individuais, Grupos (Baileys) para interações em grupo
              </Text>
            }
            data={[
              { value: 'webjs', label: 'Direto (Web.js)' },
              { value: 'bailey', label: 'Grupos (Baileys)' }
            ]}
            value={formData.type}
            onChange={handleChange('type')}
            required
          />
          
          <Group position="right" mt="md">
            <Button variant="outline" onClick={onClose}>Cancelar</Button>
            <Button type="submit" loading={loading}>Adicionar Cliente</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};

export default AddClientForm;
