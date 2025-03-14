/**
 * Serviço de API para interações com o backend do WhatsApp
 */

// URLs da API
const API_BASE_URL = '/api';
const MESSAGING_API = `${API_BASE_URL}/messaging`;
const WHATSAPP_API = `${MESSAGING_API}/whatsapp`;

/**
 * Busca todos os clientes WhatsApp ativos
 * @returns {Promise<Array>} Lista de clientes ativos
 */
export const getActiveClients = async () => {
  try {
    const response = await fetch(`${WHATSAPP_API}/clients`);
    if (!response.ok) {
      throw new Error(`Erro ao buscar clientes: ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    console.error('Erro ao buscar clientes WhatsApp:', error);
    throw error;
  }
};

/**
 * Busca estatísticas de um cliente específico
 * @param {string} clientId ID do cliente
 * @returns {Promise<Object>} Estatísticas do cliente
 */
export const getClientStats = async (clientId) => {
  try {
    const response = await fetch(`${WHATSAPP_API}/clients/${clientId}/stats`);
    if (!response.ok) {
      throw new Error(`Erro ao buscar estatísticas: ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    console.error(`Erro ao buscar estatísticas para cliente ${clientId}:`, error);
    throw error;
  }
};

/**
 * Busca conversas recentes de um cliente
 * @param {string} clientId ID do cliente
 * @param {Object} options Opções de paginação e filtros
 * @returns {Promise<Object>} Conversas paginadas
 */
export const getRecentConversations = async (clientId, options = { page: 1, limit: 20 }) => {
  try {
    const queryParams = new URLSearchParams(options).toString();
    const response = await fetch(`${WHATSAPP_API}/clients/${clientId}/conversations?${queryParams}`);
    if (!response.ok) {
      throw new Error(`Erro ao buscar conversas: ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    console.error(`Erro ao buscar conversas para cliente ${clientId}:`, error);
    throw error;
  }
};

/**
 * Adiciona um novo cliente WhatsApp
 * @param {Object} clientData Dados do novo cliente
 * @returns {Promise<Object>} Cliente criado
 */
export const addWhatsAppClient = async (clientData) => {
  try {
    const response = await fetch(`${WHATSAPP_API}/clients`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(clientData),
    });
    
    if (!response.ok) {
      throw new Error(`Erro ao adicionar cliente: ${response.statusText}`);
    }
    
    return response.json();
  } catch (error) {
    console.error('Erro ao adicionar cliente WhatsApp:', error);
    throw error;
  }
};

/**
 * Remove um cliente WhatsApp
 * @param {string} clientId ID do cliente a ser removido
 * @returns {Promise<Object>} Resultado da operação
 */
export const removeWhatsAppClient = async (clientId) => {
  try {
    const response = await fetch(`${WHATSAPP_API}/clients/${clientId}`, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      throw new Error(`Erro ao remover cliente: ${response.statusText}`);
    }
    
    return response.json();
  } catch (error) {
    console.error(`Erro ao remover cliente ${clientId}:`, error);
    throw error;
  }
};

/**
 * Gera um novo código QR para autenticação
 * @param {string} clientId ID do cliente
 * @returns {Promise<Object>} Dados do QR code
 */
export const generateQRCode = async (clientId) => {
  try {
    const response = await fetch(`${WHATSAPP_API}/clients/${clientId}/qr`, {
      method: 'POST',
    });
    
    if (!response.ok) {
      throw new Error(`Erro ao gerar QR code: ${response.statusText}`);
    }
    
    return response.json();
  } catch (error) {
    console.error(`Erro ao gerar QR code para cliente ${clientId}:`, error);
    throw error;
  }
};

/**
 * Busca detalhes de um contato no CRM
 * @param {string} phoneNumber Número de telefone do contato
 * @returns {Promise<Object>} Dados do contato no CRM
 */
export const getContactCRMDetails = async (phoneNumber) => {
  try {
    const response = await fetch(`${API_BASE_URL}/crm/contacts/phone/${phoneNumber}`);
    if (!response.ok) {
      throw new Error(`Erro ao buscar detalhes do contato: ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    console.error(`Erro ao buscar detalhes do CRM para ${phoneNumber}:`, error);
    throw error;
  }
};
