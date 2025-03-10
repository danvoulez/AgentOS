/**
 * API de WhatsApp para o AgentOS
 * Fornece endpoints para interagir com clientes WhatsApp e obter estatísticas
 */

const express = require('express');
const router = express.Router();
const WhatsAppManager = require('./WhatsAppManager');
const { formatPhoneNumber } = require('./common/utils');

// Referência ao gerenciador de WhatsApp
let whatsappManager = null;

/**
 * Inicializa a API com o gerenciador de WhatsApp
 * @param {Object} manager Instância do WhatsAppManager
 */
const initialize = (manager) => {
  whatsappManager = manager;
};

// Middleware para verificar se o gerenciador está inicializado
const checkManagerInitialized = (req, res, next) => {
  if (!whatsappManager) {
    return res.status(500).json({ 
      error: 'WhatsAppManager não inicializado' 
    });
  }
  next();
};

// Aplicar middleware a todas as rotas
router.use(checkManagerInitialized);

/**
 * GET /api/whatsapp/clients
 * Lista todos os clientes WhatsApp ativos
 */
router.get('/clients', async (req, res) => {
  try {
    const clients = whatsappManager.getAllClients().map(client => ({
      id: client.id,
      type: client.type,
      phoneNumber: client.phoneNumber,
      isReady: client.isReady,
      name: client.name || client.id
    }));
    
    res.json(clients);
  } catch (error) {
    console.error('Erro ao buscar clientes:', error);
    res.status(500).json({ error: 'Falha ao buscar clientes', details: error.message });
  }
});

/**
 * GET /api/whatsapp/clients/:clientId
 * Obtém detalhes de um cliente específico
 */
router.get('/clients/:clientId', async (req, res) => {
  try {
    const client = whatsappManager.getClient(req.params.clientId);
    
    if (!client) {
      return res.status(404).json({ error: 'Cliente não encontrado' });
    }
    
    res.json({
      id: client.id,
      type: client.type,
      phoneNumber: client.phoneNumber,
      isReady: client.isReady,
      name: client.name || client.id,
      sessionData: client.hasSession
    });
  } catch (error) {
    console.error(`Erro ao buscar cliente ${req.params.clientId}:`, error);
    res.status(500).json({ error: 'Falha ao buscar cliente', details: error.message });
  }
});

/**
 * POST /api/whatsapp/clients
 * Adiciona um novo cliente WhatsApp
 */
router.post('/clients', async (req, res) => {
  try {
    const { phoneNumber, type, name } = req.body;
    
    if (!phoneNumber || !type) {
      return res.status(400).json({ error: 'Número de telefone e tipo são obrigatórios' });
    }
    
    if (type !== 'webjs' && type !== 'bailey') {
      return res.status(400).json({ error: 'Tipo deve ser "webjs" ou "bailey"' });
    }
    
    const clientId = name || `${type}-${formatPhoneNumber(phoneNumber)}`;
    
    // Verifica se o cliente já existe
    if (whatsappManager.hasClient(clientId)) {
      return res.status(409).json({ error: 'Cliente com este ID já existe' });
    }
    
    // Criar o cliente baseado no tipo
    let client;
    if (type === 'bailey') {
      client = await whatsappManager.createBaileyClient(clientId, phoneNumber);
    } else {
      client = await whatsappManager.createWebJsClient(clientId, phoneNumber);
    }
    
    res.status(201).json({
      id: client.id,
      type: client.type,
      phoneNumber: client.phoneNumber,
      isReady: client.isReady
    });
  } catch (error) {
    console.error('Erro ao adicionar cliente:', error);
    res.status(500).json({ error: 'Falha ao adicionar cliente', details: error.message });
  }
});

/**
 * DELETE /api/whatsapp/clients/:clientId
 * Remove um cliente WhatsApp
 */
router.delete('/clients/:clientId', async (req, res) => {
  try {
    const clientId = req.params.clientId;
    
    if (!whatsappManager.hasClient(clientId)) {
      return res.status(404).json({ error: 'Cliente não encontrado' });
    }
    
    await whatsappManager.removeClient(clientId);
    res.json({ success: true, message: 'Cliente removido com sucesso' });
  } catch (error) {
    console.error(`Erro ao remover cliente ${req.params.clientId}:`, error);
    res.status(500).json({ error: 'Falha ao remover cliente', details: error.message });
  }
});

/**
 * POST /api/whatsapp/clients/:clientId/qr
 * Gera um novo código QR para autenticação
 */
router.post('/clients/:clientId/qr', async (req, res) => {
  try {
    const clientId = req.params.clientId;
    
    if (!whatsappManager.hasClient(clientId)) {
      return res.status(404).json({ error: 'Cliente não encontrado' });
    }
    
    const result = await whatsappManager.generateQR(clientId);
    
    res.json({
      clientId,
      qrCode: result.qr,
      qrUrl: `data:image/png;base64,${result.qrBase64}`
    });
  } catch (error) {
    console.error(`Erro ao gerar QR para cliente ${req.params.clientId}:`, error);
    res.status(500).json({ error: 'Falha ao gerar QR', details: error.message });
  }
});

/**
 * GET /api/whatsapp/clients/:clientId/stats
 * Obtém estatísticas de um cliente específico
 */
router.get('/clients/:clientId/stats', async (req, res) => {
  try {
    const clientId = req.params.clientId;
    
    if (!whatsappManager.hasClient(clientId)) {
      return res.status(404).json({ error: 'Cliente não encontrado' });
    }
    
    // Aqui obteríamos estatísticas reais do sistema
    // Por enquanto, retornamos dados simulados para o frontend
    const stats = {
      messagesReceived: {
        today: Math.floor(Math.random() * 100),
        week: Math.floor(Math.random() * 500)
      },
      messagesSent: {
        today: Math.floor(Math.random() * 80),
        week: Math.floor(Math.random() * 400)
      },
      activeContacts: Math.floor(Math.random() * 50),
      responseRate: Math.floor(Math.random() * 40) + 60 // 60-100%
    };
    
    res.json(stats);
  } catch (error) {
    console.error(`Erro ao buscar estatísticas para cliente ${req.params.clientId}:`, error);
    res.status(500).json({ error: 'Falha ao buscar estatísticas', details: error.message });
  }
});

/**
 * GET /api/whatsapp/clients/:clientId/conversations
 * Obtém conversas recentes de um cliente
 */
router.get('/clients/:clientId/conversations', async (req, res) => {
  try {
    const clientId = req.params.clientId;
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 10;
    
    if (!whatsappManager.hasClient(clientId)) {
      return res.status(404).json({ error: 'Cliente não encontrado' });
    }
    
    // Aqui obteríamos conversas reais do sistema
    // Por enquanto, retornamos dados simulados para o frontend
    const totalItems = 25; // Número simulado de conversas totais
    
    // Gerar conversas de exemplo
    const conversations = [];
    const startIdx = (page - 1) * limit;
    const endIdx = Math.min(startIdx + limit, totalItems);
    
    for (let i = startIdx; i < endIdx; i++) {
      const isGroup = Math.random() > 0.7;
      conversations.push({
        id: `conv-${i}`,
        phoneNumber: `55119${Math.floor(1000000 + Math.random() * 9000000)}`,
        name: isGroup ? `Grupo ${i + 1}` : `Contato ${i + 1}`,
        isGroup,
        hasUnread: Math.random() > 0.7,
        lastMessage: {
          content: `Esta é uma mensagem de exemplo ${i + 1}`,
          timestamp: new Date(Date.now() - Math.random() * 86400000).toISOString(),
          sender: Math.random() > 0.5 ? 'user' : 'client'
        }
      });
    }
    
    res.json({
      items: conversations,
      page,
      limit,
      total: totalItems,
      hasMore: endIdx < totalItems
    });
  } catch (error) {
    console.error(`Erro ao buscar conversas para cliente ${req.params.clientId}:`, error);
    res.status(500).json({ error: 'Falha ao buscar conversas', details: error.message });
  }
});

module.exports = { router, initialize };
