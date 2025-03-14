# AgentOS

An advanced AI-driven operating system for enterprise management, combining ERP, CRM, and automated media processing capabilities.

## Core Features

- 🤖 Vox Hybrid - Central Guardian with text and voice command processing
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
- **Vox Hybrid**: Central guardian with text/voice processing and persistent memory
- **Microservices**: People, Order, Media, AI Agent, Access Control
- **Real-time Processing**: Change streams for live updates
- **Security**: Role-based access with JWT authentication

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

- **Backend**: Node.js with Express
- **Database**: MongoDB
- **AI/ML**: OpenAI API (GPT and Whisper)
- **Frontend**: React with modern UI components
- **Authentication**: JWT-based auth middleware
- **Containerization**: Docker and Docker Compose
- **CI/CD**: GitHub Actions
- **Voice Processing**: Web Speech API + OpenAI Whisper

## Getting Started

1. Clone the repository
2. Copy `.env.example` to `.env` and configure environment variables
3. Install dependencies: `npm install`
4. Start the development server: `npm run dev`
5. For production: `docker-compose up -d`

### Environment Variables

Critical environment variables to configure:

```
# OpenAI API Key (required for Vox service)
OPENAI_API_KEY=your_openai_api_key_here

# MongoDB Connection
MONGO_URI=mongodb://localhost:27017/agentos

# JWT Secret for authentication
JWT_SECRET=your_jwt_secret_here
```

### Accessing the Vox Hybrid Interface

After starting the services, access the Vox interface at:

```
http://localhost:3030
```

The Vox interface provides:

- 💬 Text-based command processing
- 🎤 Voice command processing using browser's Web Speech API
- 🧠 Persistent memory of interactions
- 🔄 Integration with all other microservices

### API Endpoints

Vox Service provides the following API endpoints:

- `POST /api/vox/text` - Process text commands
- `POST /api/vox/voice` - Process voice commands (audio file upload)
- `GET /api/vox/health` - Service health check

Full documentation coming soon.

## Roadmap de Desenvolvimento

O AgentOS segue em constante evolução, com os seguintes componentes em desenvolvimento:

### 1. Advanced Vox Hybrid Capabilities

- **Sentiment Analysis**: Automatic detection of tone and emotion in messages
- **Intent Recognition**: Automatic classification of user request objectives
- **Contextualized Responses**: Response generation based on complete interaction history
- **Entity Recognition**: Identification of products, people, and dates in messages
- **Voice Command Processing**: Natural language voice interface with transcription

### 2. Enhanced Memory System

- **Intelligent Categorization**: Automatic organization of events by relevance
- **Controlled Forgetting System**: Storage optimization while maintaining important context
- **Semantic Indexing**: Intelligent information retrieval by meaning
- **Relevance Metrics**: Importance scoring for past interactions
- **Individual and Collective Memory**: Personalized and shared knowledge base

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
