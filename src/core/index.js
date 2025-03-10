/**
 * AgentOS - Servidor principal
 * 
 * Este é o ponto de entrada principal para a aplicação AgentOS.
 * Configura o servidor Express, conecta ao MongoDB, e inicializa o VoxAgent.
 */

require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const path = require('path');
const VoxAgent = require('./VoxAgent');
const { WhatsAppIntegration } = require('../messaging/whatsapp');
const whatsappApi = require('../messaging/whatsapp/api');

// Inicialização da aplicação
const app = express();
const PORT = process.env.PORT || 3000;
const MONGO_URL = process.env.MONGO_URL || 'mongodb://localhost:27017/agentos';

// Middlewares básicos
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Servir arquivos estáticos da aplicação React
app.use(express.static(path.join(__dirname, '../../dist')));

// Variável global para armazenar referência ao VoxAgent
let voxAgent = null;
let whatsappIntegration = null;

// Rota de verificação de saúde
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    services: {
      database: mongoose.connection.readyState === 1 ? 'connected' : 'disconnected',
      voxAgent: voxAgent?.state?.isInitialized ? 'initialized' : 'not initialized',
      whatsapp: whatsappIntegration ? 'initialized' : 'not initialized'
    }
  });
});

// Adicionar rotas da API WhatsApp
app.use('/api/whatsapp', whatsappApi.router);

// Servir a aplicação React para qualquer outra rota
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../../dist/index.html'));
});

// Inicialização do servidor
async function startServer() {
  try {
    console.log('Iniciando AgentOS...');
    
    // Conectar ao MongoDB
    console.log(`Conectando ao MongoDB em ${MONGO_URL}...`);
    const mongoConnection = await mongoose.connect(MONGO_URL, {
      useNewUrlParser: true,
      useUnifiedTopology: true
    });
    console.log('Conexão com MongoDB estabelecida');
    
    // Inicializar VoxAgent
    console.log('Inicializando VoxAgent...');
    voxAgent = new VoxAgent();
    await voxAgent.initialize(mongoConnection);
    console.log('VoxAgent inicializado com sucesso');
    
    // Inicializar integração com WhatsApp
    console.log('Inicializando integração com WhatsApp...');
    whatsappIntegration = new WhatsAppIntegration(voxAgent, {
      sessionsDir: path.join(__dirname, '../../.whatsapp-sessions'),
      mediaDir: path.join(__dirname, '../../media')
    });
    await whatsappIntegration.initialize();
    
    // Configurar API de WhatsApp com o gerenciador
    whatsappApi.initialize(whatsappIntegration.manager);
    console.log('Integração com WhatsApp inicializada com sucesso');
    
    // Iniciar o servidor HTTP
    app.listen(PORT, () => {
      console.log(`Servidor AgentOS rodando na porta ${PORT}`);
      console.log(`Interface de administração disponível em http://localhost:${PORT}`);
    });
    
    // Configurar handlers para encerramento limpo
    setupShutdownHandlers();
    
  } catch (error) {
    console.error('Erro ao iniciar o servidor:', error);
    process.exit(1);
  }
}

// Configurar handlers para encerramento limpo
function setupShutdownHandlers() {
  async function shutdown() {
    console.log('Encerrando AgentOS...');
    
    // Encerrar integração com WhatsApp
    if (whatsappIntegration) {
      console.log('Encerrando integração com WhatsApp...');
      await whatsappIntegration.shutdown();
    }
    
    // Encerrar VoxAgent
    if (voxAgent) {
      console.log('Encerrando VoxAgent...');
      await voxAgent.shutdown();
    }
    
    // Encerrar conexão com MongoDB
    if (mongoose.connection.readyState === 1) {
      console.log('Fechando conexão com MongoDB...');
      await mongoose.connection.close();
    }
    
    console.log('AgentOS encerrado com sucesso');
    process.exit(0);
  }
  
  // Capturar sinais de encerramento
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
  process.on('uncaughtException', (error) => {
    console.error('Exceção não tratada:', error);
    shutdown();
  });
}

// Iniciar o servidor
startServer();
