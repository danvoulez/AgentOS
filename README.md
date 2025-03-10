# AgentOS

An advanced AI-driven operating system for enterprise management, combining ERP, CRM, and automated media processing capabilities.

## Core Features

- 🤖 AI Agent (VoxAgent) for system orchestration
- 💼 Enterprise Resource Planning (ERP)
- 👥 Customer Relationship Management (CRM)
- 🎥 Automated Video Processing with Face Recognition
- 🏦 Integrated Banking System
- 📱 WhatsApp Integration with CRM Dashboard
- 🔐 Multi-Role Access Control
- 🎨 GitKraken-Inspired UI

## System Architecture

### Data Layer (MongoDB)
- **People Collection**: Unified profiles with multi-role support
- **Media Collection**: Video/photo metadata with face detection
- **Events Collection**: System-wide event tracking
- **Transactions Collection**: Financial operations tracking
- **NAS Integration**: Local video storage with MongoDB references

### Service Layer
- **AI Core**: Central intelligence hub (VoxAgent)
- **Microservices**: ERP, CRM, Media Processing
- **Real-time Processing**: Change streams for live updates
- **Security**: Role-based access with audit logging

## MongoDB Schema Highlights

### People Collection
```javascript
{
  _id: ObjectId,
  name: String,
  roles: ['client', 'reseller'],
  faceEmbedding: Binary,
  bankAccount: {
    balance: Decimal128,
    transactions: [{ type, amount, date }]
  },
  mediaAccess: [{
    videoId: ObjectId,
    timestamps: []
  }]
}
```

### Media Collection
```javascript
{
  _id: ObjectId,
  type: 'video',
  nasPath: String,
  faceDetections: [{
    personId: ObjectId,
    timestamp: Date,
    confidence: Number
  }],
  highlights: [{
    start: String,
    end: String,
    personId: ObjectId
  }]
}
```

## Tech Stack

- **Backend**: Node.js, Python
- **Database**: MongoDB Atlas (Cloud) + Local MongoDB
- **AI/ML**: TensorFlow/PyTorch
- **Message Queue**: Kafka/RabbitMQ
- **UI**: React with dark theme
- **Video Processing**: FFmpeg
- **WhatsApp**: Baileys integration

## Getting Started

1. Install MongoDB locally or set up MongoDB Atlas
2. Configure NAS connection for video storage
3. Set up environment variables
4. Run npm install
5. Start the VoxAgent core

### Starting the WhatsApp Dashboard

```bash
# Para executar apenas o cliente WhatsApp (com QR code no terminal)
npm run whatsapp:start

# Para executar o dashboard completo integrado ao CRM
npm run dashboard
```

Acesse o dashboard em `http://localhost:3000/whatsapp` após iniciar o servidor.

### Funcionalidades do Dashboard WhatsApp

- 📊 Visualização de estatísticas de mensagens por cliente
- 👥 Gerenciamento de múltiplos números WhatsApp
- 🔄 Integração direta com o CRM para visualizar perfis de clientes
- 📱 Suporte para diferentes tipos de clientes (grupos vs. direto)
- 📈 Métricas de desempenho e engajamento

Full documentation coming soon.

## Roadmap de Desenvolvimento

O AgentOS segue em constante evolução, com os seguintes componentes em desenvolvimento:

### 1. Sistema de NLP Avançado para o VoxAgent

- **Análise de Sentimento**: Detecção automática do tom e emoção nas mensagens
- **Detecção de Intenções**: Classificação automática do objetivo da mensagem do cliente
- **Respostas Contextualizadas**: Geração de respostas com base no histórico completo
- **Reconhecimento de Entidades**: Identificação de produtos, pessoas e datas em mensagens

### 2. Aprimoramento do Sistema de Memória

- **Categorização Inteligente**: Organização automática de eventos por relevância
- **Sistema de Esquecimento Controlado**: Otimização de armazenamento mantendo contexto importante
- **Indexação Semântica**: Recuperação inteligente de informações por significado
- **Métricas de Relevância**: Pontuação de importância para interações passadas

### 3. Automações e Fluxos de Trabalho

- **Editor Visual de Fluxos**: Interface para criar respostas automáticas sem código
- **Gatilhos Complexos**: Ações automatizadas baseadas em múltiplas condições
- **Integração com Calendário**: Agendamento automático de compromissos via WhatsApp
- **Notificações Proativas**: Envio automático de lembretes e atualizações

### 4. Segurança e Conformidade

- **Criptografia Avançada**: Proteção de dados em trânsito e em repouso
- **Conformidade LGPD/GDPR**: Ferramentas para gestão de consentimento e direito ao esquecimento
- **Sistema de Auditoria**: Registro detalhado de todas as interações e alterações
- **Política de Retenção**: Configurações para exclusão automática de dados antigos

## License

Proprietary - All rights reserved
